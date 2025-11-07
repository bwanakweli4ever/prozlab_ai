# app/services/sms_service.py
import random
import string
import json
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory storage for OTP.")

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. Using development mode for SMS.")

# In-memory storage for development mode (when Redis is not available)
otp_storage = {}
rate_limit_storage = {}


class SMSService:
    def __init__(self):
        self.twilio_configured = settings.is_sms_enabled() and TWILIO_AVAILABLE
        self.development_mode = not self.twilio_configured
        
        if self.twilio_configured:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_number = settings.TWILIO_PHONE_NUMBER
            logger.info("Twilio SMS service initialized successfully")
        else:
            self.client = None
            self.from_number = None
            logger.info("SMS service running in DEVELOPMENT MODE")
        
        # Set up storage (Redis or in-memory)
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                # Test Redis connection
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Redis connection failed: {str(e)}. Using in-memory storage.")
                self.redis_client = None
                self.use_redis = False
        else:
            self.redis_client = None
            self.use_redis = False
            logger.info("Using in-memory storage for OTP (development mode)")
    
    def generate_otp(self, length: int = None) -> str:
        """Generate a random OTP code"""
        length = length or settings.OTP_LENGTH
        return ''.join(random.choices(string.digits, k=length))
    
    def _get_rate_limit_key(self, phone_number: str) -> str:
        """Get key for rate limiting"""
        return f"otp_rate_limit:{phone_number}"
    
    def _get_otp_key(self, phone_number: str) -> str:
        """Get key for OTP storage"""
        return f"otp:{phone_number}"
    
    def _store_data(self, key: str, data: dict, expire_seconds: int = None):
        """Store data in Redis or in-memory"""
        if self.use_redis:
            self.redis_client.setex(key, expire_seconds or 3600, json.dumps(data))
        else:
            # In-memory storage with expiration
            expire_at = datetime.utcnow() + timedelta(seconds=expire_seconds or 3600)
            if key.startswith("otp_rate_limit:"):
                rate_limit_storage[key] = {"data": data, "expires_at": expire_at}
            else:
                otp_storage[key] = {"data": data, "expires_at": expire_at}
    
    def _get_data(self, key: str) -> Optional[dict]:
        """Get data from Redis or in-memory"""
        if self.use_redis:
            data_str = self.redis_client.get(key)
            return json.loads(data_str) if data_str else None
        else:
            # In-memory storage with expiration check
            storage = rate_limit_storage if key.startswith("otp_rate_limit:") else otp_storage
            if key in storage:
                stored = storage[key]
                if datetime.utcnow() < stored["expires_at"]:
                    return stored["data"]
                else:
                    # Expired, remove it
                    del storage[key]
            return None
    
    def _delete_data(self, key: str):
        """Delete data from Redis or in-memory"""
        if self.use_redis:
            self.redis_client.delete(key)
        else:
            # Remove from appropriate storage
            if key.startswith("otp_rate_limit:") and key in rate_limit_storage:
                del rate_limit_storage[key]
            elif key in otp_storage:
                del otp_storage[key]
    
    def _increment_rate_limit(self, phone_number: str):
        """Increment rate limit counter"""
        key = self._get_rate_limit_key(phone_number)
        current_data = self._get_data(key) or {"count": 0}
        current_data["count"] += 1
        self._store_data(key, current_data, 3600)  # 1 hour expiry
    
    def _check_rate_limit(self, phone_number: str) -> bool:
        """Check if phone number has exceeded rate limit"""
        key = self._get_rate_limit_key(phone_number)
        data = self._get_data(key)
        
        if not data:
            return True  # No previous requests
        
        return data.get("count", 0) < 3  # Max 3 SMS per hour
    
    def send_otp(self, phone_number: str) -> dict:
        """Send OTP via SMS"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(phone_number):
                return {
                    "success": False,
                    "message": "Too many SMS requests. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            
            # Generate OTP
            otp_code = self.generate_otp()
            
            # Store OTP
            otp_data = {
                "code": otp_code,
                "attempts": 0,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)).isoformat()
            }
            
            otp_key = self._get_otp_key(phone_number)
            self._store_data(otp_key, otp_data, settings.OTP_EXPIRE_MINUTES * 60)
            
            # Send SMS or log in development mode
            if self.development_mode:
                # Development mode - log OTP
                logger.info(f"🔐 DEVELOPMENT MODE - OTP for {phone_number}: {otp_code}")
                print(f"🔐 DEVELOPMENT MODE - OTP for {phone_number}: {otp_code}")
                
                message = f"OTP sent successfully (development mode). Check console for OTP: {otp_code}"
                message_sid = f"dev_msg_{random.randint(1000, 9999)}"
            else:
                # Production mode - send actual SMS
                message_body = f"Your verification code is: {otp_code}. This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes."
                
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_number,
                    to=phone_number
                )
                message_sid = message.sid
                message = "OTP sent successfully"
            
            # Increment rate limit
            self._increment_rate_limit(phone_number)
            
            return {
                "success": True,
                "message": message,
                "expires_in_minutes": settings.OTP_EXPIRE_MINUTES,
                "message_sid": message_sid,
                "development_mode": self.development_mode
            }
            
        except Exception as e:
            if TWILIO_AVAILABLE and not self.development_mode:
                if isinstance(e, TwilioException):
                    logger.error(f"Twilio error sending OTP to {phone_number}: {str(e)}")
                    return {
                        "success": False,
                        "message": "Failed to send SMS. Please check your phone number.",
                        "error_code": "SMS_SEND_FAILED",
                        "error_details": str(e)
                    }
            
            logger.error(f"Unexpected error sending OTP to {phone_number}: {str(e)}")
            return {
                "success": False,
                "message": "An unexpected error occurred",
                "error_code": "INTERNAL_ERROR"
            }
    
    def verify_otp(self, phone_number: str, otp_code: str) -> dict:
        """Verify OTP code"""
        try:
            otp_key = self._get_otp_key(phone_number)
            otp_data = self._get_data(otp_key)
            
            if not otp_data:
                return {
                    "success": False,
                    "message": "OTP expired or not found. Please request a new one.",
                    "error_code": "OTP_NOT_FOUND"
                }
            
            # Check if OTP has expired
            expires_at = datetime.fromisoformat(otp_data["expires_at"])
            if datetime.utcnow() > expires_at:
                self._delete_data(otp_key)
                return {
                    "success": False,
                    "message": "OTP has expired. Please request a new one.",
                    "error_code": "OTP_EXPIRED"
                }
            
            # Check attempts
            if otp_data["attempts"] >= settings.MAX_OTP_ATTEMPTS:
                self._delete_data(otp_key)
                return {
                    "success": False,
                    "message": "Maximum verification attempts exceeded. Please request a new OTP.",
                    "error_code": "MAX_ATTEMPTS_EXCEEDED"
                }
            
            # Verify OTP
            if otp_data["code"] == otp_code:
                # OTP is correct - delete it
                self._delete_data(otp_key)
                
                logger.info(f"✅ OTP verified successfully for {phone_number}")
                return {
                    "success": True,
                    "message": "Phone number verified successfully",
                    "phone_verified": True
                }
            else:
                # Increment attempts
                otp_data["attempts"] += 1
                remaining_attempts = settings.MAX_OTP_ATTEMPTS - otp_data["attempts"]
                
                if remaining_attempts > 0:
                    # Update attempts
                    remaining_time = int((expires_at - datetime.utcnow()).total_seconds())
                    self._store_data(otp_key, otp_data, remaining_time)
                    
                    return {
                        "success": False,
                        "message": f"Invalid OTP. {remaining_attempts} attempts remaining.",
                        "error_code": "INVALID_OTP",
                        "remaining_attempts": remaining_attempts
                    }
                else:
                    # Max attempts exceeded
                    self._delete_data(otp_key)
                    return {
                        "success": False,
                        "message": "Maximum verification attempts exceeded. Please request a new OTP.",
                        "error_code": "MAX_ATTEMPTS_EXCEEDED"
                    }
            
        except Exception as e:
            logger.error(f"Error verifying OTP for {phone_number}: {str(e)}")
            return {
                "success": False,
                "message": "An error occurred during verification",
                "error_code": "VERIFICATION_ERROR"
            }

    def get_service_status(self) -> dict:
        """Get the current status of the SMS service"""
        return {
            "sms_configured": self.twilio_configured,
            "redis_available": self.use_redis,
            "twilio_available": TWILIO_AVAILABLE,
            "redis_library_available": REDIS_AVAILABLE,
            "development_mode": self.development_mode,
            "storage_type": "redis" if self.use_redis else "in-memory"
        }
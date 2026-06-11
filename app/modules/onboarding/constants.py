"""Onboarding step definitions aligned with the Prozlab frontend wizard."""

ONBOARDING_STEPS = [
    "welcome",
    "expertise",
    "experience",
    "preferences",
    "portfolio",
    "skills_verification",
    "profile",
]

EXPERIENCE_LEVEL_MAP = {
    "0-1 years": 0,
    "1-3 years": 2,
    "3-5 years": 4,
    "5+ years": 7,
}

HIRING_SPECIALTIES = [
    ("Computer Repair", "Hardware diagnostics, troubleshooting, and repair"),
    ("Network Setup", "LAN/WAN configuration, Wi-Fi, and network security"),
    ("Data Recovery", "Backup, restore, and disaster recovery services"),
    ("Mobile Repair", "Smartphone and tablet hardware and software repair"),
    ("Hardware Install", "Server, workstation, and peripheral installation"),
    ("Software Support", "OS, application, and end-user technical support"),
    ("Web Development", "Websites, web apps, and frontend/backend development"),
    ("Digital Marketing", "SEO, social media, ads, and growth marketing"),
    ("Product Design", "UI/UX, design systems, and user research"),
    ("Software Engineering", "Full-stack, backend, and frontend development"),
    ("Data & Analytics", "Data science, BI, and analytics engineering"),
    ("Cybersecurity", "Security engineering and compliance"),
    ("Cloud & DevOps", "Infrastructure, SRE, and cloud architecture"),
    ("Project Management", "Agile delivery and cross-functional leadership"),
    ("Business Consulting", "Strategy, operations, and advisory"),
]

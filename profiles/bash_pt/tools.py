"""
BASH.PT-specific tools.
Registered on top of core ToolRegistry defaults.

These tools extend the agent's capabilities for the cybersecurity consultancy context.
"""

from datetime import datetime
from core.tools import Tool, ToolType


BASH_PT_SERVICES = {
    "pentest": {
        "name": "Penetration Testing",
        "description": "Simulated cyberattacks to identify vulnerabilities before attackers do.",
        "formats": ["Black Box", "Grey Box", "White Box"],
        "contact": "geral@bash.pt",
    },
    "audit": {
        "name": "Security Audit",
        "description": "Comprehensive review of security posture, policies, and controls.",
        "formats": ["Technical", "Compliance", "Executive"],
        "contact": "geral@bash.pt",
    },
    "incident": {
        "name": "Incident Response",
        "description": "Rapid containment, investigation, and recovery from security incidents.",
        "formats": ["Retainer", "On-demand"],
        "contact": "geral@bash.pt",
    },
    "training": {
        "name": "Executive Security Training",
        "description": "Board-level and C-suite cybersecurity awareness and governance training.",
        "formats": ["Workshop", "Tabletop Exercise", "Ongoing Advisory"],
        "contact": "geral@bash.pt",
    },
    "compliance": {
        "name": "Compliance Consulting",
        "description": "Gap analysis and roadmap for ISO 27001, NIS2, DORA, GDPR.",
        "formats": ["Gap Analysis", "Remediation Roadmap", "Audit Readiness"],
        "contact": "geral@bash.pt",
    },
}

# ── Tool handlers ─────────────────────────────────────────────────────────────

def handle_get_services(service_type: str = None) -> dict:
    """Return BASH.PT service info."""
    if service_type and service_type.lower() in BASH_PT_SERVICES:
        svc = BASH_PT_SERVICES[service_type.lower()]
        return {
            "service": svc["name"],
            "description": svc["description"],
            "formats": svc["formats"],
            "next_step": f"Contact us at {svc['contact']} to discuss your requirements.",
        }
    return {
        "services": [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in BASH_PT_SERVICES.items()
        ],
        "note": "Ask about any specific service for more detail.",
    }


def handle_request_contact(service: str = None, urgency: str = "normal") -> dict:
    """Generate a contact prompt for the visitor."""
    return {
        "action": "contact_form",
        "message": "To connect with our team, please use the contact form on bash.pt or email geral@bash.pt.",
        "service_interest": service,
        "urgency": urgency,
        "response_time": "within 24 hours" if urgency != "urgent" else "within 4 hours",
    }


def handle_get_threat_context(sector: str = None) -> dict:
    """Provide high-level threat context relevant to the visitor's sector."""
    contexts = {
        "finance": "Financial institutions are primary targets for ransomware, BEC fraud, and supply-chain attacks. DORA compliance is now mandatory in the EU.",
        "healthcare": "Healthcare faces escalating ransomware and data exfiltration. NIS2 extends obligations to critical health infrastructure.",
        "telecoms": "Telecoms are subject to SS7/Diameter exploitation, insider threats, and state-sponsored espionage. NIS2 applies directly.",
        "manufacturing": "OT/ICS environments increasingly targeted. Legacy systems and IT/OT convergence create critical exposure.",
        "legal": "Law firms hold high-value confidential data with historically weak security postures — a top target for corporate espionage.",
    }
    if sector and sector.lower() in contexts:
        return {
            "sector": sector,
            "threat_context": contexts[sector.lower()],
            "recommendation": "Ask about a tailored security assessment for your sector.",
        }
    return {
        "general_context": "Cyberthreats are sector-agnostic. Phishing, ransomware, and supply-chain attacks affect all industries.",
        "available_sectors": list(contexts.keys()),
    }


# ── Tool definitions ──────────────────────────────────────────────────────────

BASH_PT_TOOLS = [
    Tool(
        name="get_bash_services",
        description="Get information about BASH.PT's cybersecurity services. Use when visitor asks what services BASH offers.",
        parameters={
            "service_type": {
                "type": "string",
                "description": "Service identifier: pentest, audit, incident, training, compliance. Omit for full list.",
                "required": False,
            }
        },
        tool_type=ToolType.INFORMATION,
        handler=lambda **kw: handle_get_services(**kw),
    ),
    Tool(
        name="request_contact",
        description="Generate contact instructions when visitor wants to reach BASH.PT or request a proposal.",
        parameters={
            "service": {
                "type": "string",
                "description": "Service the visitor is interested in.",
                "required": False,
            },
            "urgency": {
                "type": "string",
                "enum": ["normal", "urgent"],
                "description": "Urgency level.",
                "required": False,
            },
        },
        tool_type=ToolType.ACTION,
        handler=lambda **kw: handle_request_contact(**kw),
    ),
    Tool(
        name="get_threat_context",
        description="Provide relevant cyberthreat context for visitor's industry sector.",
        parameters={
            "sector": {
                "type": "string",
                "description": "Industry sector: finance, healthcare, telecoms, manufacturing, legal.",
                "required": False,
            }
        },
        tool_type=ToolType.INFORMATION,
        handler=lambda **kw: handle_get_threat_context(**kw),
    ),
]


def register_tools(registry) -> None:
    """Register all BASH.PT tools onto an existing ToolRegistry."""
    for tool in BASH_PT_TOOLS:
        registry.register(tool)

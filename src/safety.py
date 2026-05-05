import re
from typing import Tuple, Optional

class SafetyGuard:
    def __init__(self):
        # Harmful patterns per category
        self.patterns = {
            "insider_trading": [
                r"unannounced acquisition",
                r"friend at .* tip",
                r"material non-public",
                r"confidential merger",
                r"insider info",
                r"know about an? (unannounced|confidential)",
                r"before (tomorrow's|the) announcement",
                r"trade on .* confidential"
            ],
            "market_manipulation": [
                r"pump (up )?the price",
                r"pump and dump",
                r"coordinated buying scheme",
                r"wash trade",
                r"move this stock \d+%",
                r"spoofing and layering" # Though educational uses this, we need to be careful
            ],
            "money_laundering": [
                r"without reporting it",
                r"avoid the .* reporting threshold",
                r"obscure the source of (these )?funds",
                r"hide trading profits",
                r"layer my trades",
                r"move .* cash through stock"
            ],
            "guaranteed_returns": [
                r"guarantee (me )?[\d\.]+% returns",
                r"promise (me )?my money will double",
                r"100% certain to go up",
                r"foolproof way to make",
                r"guarantee(d)? returns?"
            ],
            "reckless_advice": [
                r"all my retirement savings in crypto",
                r"put my entire emergency fund into",
                r"mortgage my house for",
                r"take a margin loan to buy"
            ],
            "sanctions_evasion": [
                r"bypass OFAC sanctions",
                r"sanctioned .* company without it being traced",
                r"route trades through a shell company"
            ],
            "fraud": [
                r"fake contract note",
                r"claim losses"
            ]
        }

        # Keywords that suggest educational intent
        self.educational_keywords = [
            r"what is", r"explain", r"describe", r"how does", r"what are", 
            r"penalties", r"regulations", r"difference between", r"historical",
            r"compliance", r"obligations", r"role in", r"is .* illegal", r"factors should .* consider"
        ]

    def check_query(self, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        query_lower = query.lower()
        
        # Check for educational intent first (to avoid over-blocking)
        is_educational = any(re.search(pattern, query_lower) for pattern in self.educational_keywords)
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    # If it matches a harmful pattern but also looks educational, 
                    # we might still want to block if the harmful pattern is very specific.
                    # But the requirement says ≥90% pass-through on educational.
                    if is_educational:
                        # Specific override: if they ask "how to do [bad thing]", block even if "how" is educational
                        if query_lower.startswith("how do i") or query_lower.startswith("how can i") or "help me" in query_lower:
                             return True, category, self.get_refusal_message(category)
                        continue
                    
                    return True, category, self.get_refusal_message(category)
        
        return False, None, None

    def get_refusal_message(self, category: str) -> str:
        messages = {
            "insider_trading": "I cannot assist with requests involving material non-public information or potential insider trading. This is illegal and violates financial regulations.",
            "market_manipulation": "I cannot help with strategies intended to manipulate market prices or create artificial trading volume. Such activities are prohibited.",
            "money_laundering": "I am unable to provide assistance with transactions that appear designed to evade reporting requirements or obscure the source of funds.",
            "guaranteed_returns": "I cannot guarantee specific investment returns. All investments carry risk, and promising fixed or 'certain' profits is misleading and often fraudulent.",
            "reckless_advice": "I cannot recommend high-risk strategies that jeopardize your core financial security, such as investing entire emergency funds or retirement savings into volatile assets.",
            "sanctions_evasion": "I cannot assist with efforts to bypass international sanctions or trade with prohibited entities.",
            "fraud": "I cannot assist with the creation of fraudulent documents or deceptive financial practices."
        }
        return messages.get(category, "I cannot fulfill this request as it involves potentially harmful or prohibited financial activities.")

safety_guard = SafetyGuard()

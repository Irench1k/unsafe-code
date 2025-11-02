"""Shared database for cross-component parsing confusion examples."""

db = {
    "messages": {
        "spongebob": [
            {
                "id": 1,
                "from": "patrick",
                "text": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!",
                "read": False,
            }
        ],
        "squidward": [
            {
                "id": 2,
                "from": "squidward",
                "text": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number.",
                "read": True,
            },
        ],
        "mr.krabs": [
            {
                "id": 3,
                "from": "squidward",
                "text": "I saw Plankton lurking around with a mechanical keyboard. He's planning something!",
                "read": False,
            },
        ],
        "plankton": [
            {
                "id": 4,
                "from": "system",
                "text": "Welcome to the system! Please complete your onboarding process.",
                "read": True,
            }
        ],
    },
    "profiles": {
        "spongebob": {
            "display_name": "SpongeBob SquarePants",
            "bio": "I'm ready! Fry cook at the Krusty Krab.",
            "password": "bikinibottom",
        },
        "squidward": {
            "display_name": "Squidward Tentacles",
            "bio": "Clarinet enthusiast and cashier.",
            "password": "clarinet123",
        },
        "mr.krabs": {
            "display_name": "Eugene Krabs",
            "bio": "Owner of the Krusty Krab. I love money!",
            "password": "money",
        },
        "plankton": {
            "display_name": "Sheldon Plankton",
            "bio": "Computer scientist and entrepreneur.",
            "password": "chumbucket",
        },
    },
    "next_message_id": 5,
}

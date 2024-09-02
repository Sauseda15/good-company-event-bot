async def switch_to_token(token: str) -> str:
    token_urls = {
        "Event Token": "https://drive.google.com/file/d/1ioi8s17Da6-f7llwg9tiVAtQztz3o479/view?usp=drive_link",
        "Leadership Token": "https://drive.google.com/file/d/1f-ml9i5GuvQLn5mL2u8hzzCD3hcgrsXR/view?usp=drive_link",
        "Competitive Token": "https://drive.google.com/file/d/1WAPLeau4w2i-g6LGAVVDIdD-h73YUydZ/view?usp=drive_link",
        "War Token": "https://drive.google.com/file/d/1Qno6hchFbxPTBrmpUAOJlJqfTqXUhJW_/view?usp=drive_link"
    }
    return token_urls.get(token, None)

async def event_token_add(member_id: int, company: str, bank: dict, token: str) -> tuple:
    member_id_str = str(member_id)
    bank.setdefault(company, {}).setdefault(member_id_str, {}).setdefault(token, 0)

    start_balance = bank[company][member_id_str][token]
    bank[company][member_id_str][token] += 1
    end_balance = bank[company][member_id_str][token]

    return start_balance, end_balance, bank

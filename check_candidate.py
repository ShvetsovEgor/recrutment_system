from database import db

# Проверяем существование кандидата
candidate_id = '1d0d1a5e-a6a4-4f21-8ba0-5124c3bb9597'
candidate = db.get_candidate_by_id(candidate_id)

print(f"Candidate found: {candidate is not None}")
if candidate:
    print(f"Candidate name: {candidate.get('name', 'N/A')}")
    print(f"Candidate email: {candidate.get('email', 'N/A')}")
else:
    print("Candidate not found")

# Проверяем все кандидаты
all_candidates = db.get_all_candidates()
print(f"\nTotal candidates in database: {len(all_candidates)}")
if all_candidates:
    print("First few candidates:")
    for i, c in enumerate(all_candidates[:3]):
        print(f"{i+1}. {c.get('name', 'N/A')} (ID: {c.get('id', 'N/A')[:8]}...)") 
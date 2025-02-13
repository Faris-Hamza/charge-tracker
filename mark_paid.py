
from database import Database

def main():
    db = Database()
    try:
        db.mark_all_transactions_as_paid()
        print("Toutes les transactions ont été marquées comme payées avec succès!")
    except Exception as e:
        print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    main()

"""
Test script to fetch all SPX option contracts and save to CSV
"""
import asyncio
import csv
from datetime import datetime
from app.services.tradelist.client import TradeListClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def fetch_and_save_spx_contracts():
    """Fetch all SPX contracts and save to CSV"""

    # Create TradeList client
    client = TradeListClient()

    print("Fetching SPX option contracts...")
    print("This may take 1-2 minutes due to pagination...")

    try:
        async with client:
            # Fetch all SPX contracts with pagination
            contracts = await client.get_options_contracts("SPX", limit=1000)

            print(f"\nTotal contracts retrieved: {len(contracts)}")

            if not contracts:
                print("No contracts retrieved!")
                return

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"spx_contracts_{timestamp}.csv"

            # Write to CSV
            with open(filename, 'w', newline='') as csvfile:
                if contracts:
                    # Get field names from first contract
                    fieldnames = contracts[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    # Write header
                    writer.writeheader()

                    # Write all contracts
                    for contract in contracts:
                        writer.writerow(contract)

            print(f"\nContracts saved to: {filename}")

            # Print summary statistics
            if contracts:
                # Count by expiration date
                expiration_counts = {}
                for contract in contracts:
                    exp_date = contract.get('expiration_date', 'unknown')
                    expiration_counts[exp_date] = expiration_counts.get(exp_date, 0) + 1

                print("\n--- Summary Statistics ---")
                print(f"Total contracts: {len(contracts)}")
                print(f"Unique expiration dates: {len(expiration_counts)}")

                # Sort by expiration date and show first 10
                sorted_exp = sorted(expiration_counts.items())[:10]
                print("\nFirst 10 expiration dates and contract counts:")
                for exp_date, count in sorted_exp:
                    print(f"  {exp_date}: {count} contracts")

                # Count by contract type
                call_count = sum(1 for c in contracts if c.get('contract_type') == 'call')
                put_count = sum(1 for c in contracts if c.get('contract_type') == 'put')
                print(f"\nContract types:")
                print(f"  Calls: {call_count}")
                print(f"  Puts: {put_count}")

                # Sample contract for verification
                print("\nSample contract (first one):")
                for key, value in contracts[0].items():
                    print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error fetching contracts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the async function
    asyncio.run(fetch_and_save_spx_contracts())
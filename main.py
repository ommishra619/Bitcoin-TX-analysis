from data_fetcher import get_address_info
from bitcoin_basics import summarize_address
address=input ("Enter bitcoin address:")
info=get_address_info(address)
summary=summarize_address(info)

print("\n------WALLET SUMMARY-----")
for key, value in summary.items():
     print(f"{key}: {value}")
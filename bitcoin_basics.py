def summarize_address(data):
    chain_stats=data.get("chain_stats",{})
    total_received=chain_stats.get("fund_txo_sum",0)
    total_sent= chain_stats.get("spent_txo_sum",0)
    tx_count=chain_stats.get("tx_count",0)

    balance= total_received-total_sent
    return{
        "total_received":total_received/1e8,
        "total_sent":total_sent/1e8,
        "balance":balance/1e8,
        "tx_count":tx_count
    }

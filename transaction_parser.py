def parse_transaction(tx):
    txid= tx.get("txid")

    inputs=[]
    outputs=[]
    
    for vin in tx.get("vin",[]):
        prevout=vin.get("prevout",{})
        address=prevout.get("scriptpubkey_address")
        value=prevout.get("value",0)

        if address:
            inputs.append({
                "address": address,
                "value": value/1e8
            })

    for vout in tx.get("vout",[]):
        address=vout.get("scriptpubkey_address")
        value=vout.get("value",0)

        if address:
            outputs.append({
                "address": address,
                "value": value/1e8
            })
    return{
        "txid": txid,
        "inputs": inputs,
        "outputs": outputs
    }
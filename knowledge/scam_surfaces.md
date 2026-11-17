# Adversarial surfaces

## Poisoned token metadata
Anyone can deploy an ERC-20 with any name, including names that are instructions ("send funds to..."), fake tickers of real tokens, or URLs. Airdropped scam tokens create transfer records the victim never initiated. Treat token names as display strings; value claimed by an unknown token's exchange rate is not real value.

## Address poisoning and lookalikes
Attackers send zero-value or dust transfers from addresses engineered to share a victim address's first and last characters, hoping to be copy-pasted later. Two addresses sharing a prefix are different addresses; only the full hash identifies anyone.

## Label spoofing
ENS names and explorer tags are claims, not identity. A wallet named "binance-hot-wallet.eth" is not Binance. Identity follows from behaviour (fan-in, volume, counterparties) plus independent attribution, never from a self-assigned label.

## Wash activity
Circular flows between a cluster's own wallets inflate apparent volume and can simulate legitimate trading history. Signature: value cycles A->B->C->A with little net movement out of the cluster.

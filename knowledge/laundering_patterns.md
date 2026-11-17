# Laundering typologies

## Peel chains
Stolen funds hop through a chain of fresh wallets, each passing most of the balance forward and "peeling" a small amount to a side address, often an exchange deposit. Signature: wallets with pass-through ratio near 1, fan-in 1, fan-out 2, short activity spans measured in hours, and depth increasing one step per hop.

## Fan-out / fan-in (smurfing)
Funds split from one wallet into many mid-size wallets and later reconverge at one or two collection points. Signature: a node with high fan-out of similar amounts in a short window, mirrored later by a node with the same fan-in. The collection point, not the smurf wallets, is the address worth expanding.

## Mixers and privacy pools
Deposits into a mixer are fixed denominations to a well-known contract; tracing through is not possible on-chain, so the finding is the deposit itself: amount, timing and who sent it. Expanding a mixer contract wastes budget.

## Exchange deposit addresses
Fresh wallets that receive one or a few transfers and immediately forward to a hot wallet with huge fan-in. The deposit address identifies the cash-out venue and roughly when: that is a finding and a subpoena target, not a dead end to crawl further.

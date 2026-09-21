# PriceWire

Applicant wallet: 0x6ce54b4c551df40808742703fa435e52b88d621f
Built for the GenLayer Judgment Hackathon.

PriceWire stores the latest ETH price on chain. The contract fetches a price
API and every validator must read the same number.

The price is a plain number from a public API, so the contract compares it
exactly. There is no judgment step; the contract is a price feed.

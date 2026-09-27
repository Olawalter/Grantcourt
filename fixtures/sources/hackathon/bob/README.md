# PriceWire

Applicant wallet: 0x81de1a008d476280fb6890bd8c6949cf91e3d6d0
Built for the GenLayer Judgment Hackathon.

PriceWire stores the latest ETH price on chain. The contract fetches a price
API and every validator must read the same number.

The price is a plain number from a public API, so the contract compares it
exactly. There is no judgment step; the contract is a price feed.

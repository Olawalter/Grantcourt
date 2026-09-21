# Settlement adapter integration guide

## Install
Add the adapter address to your configuration.

## Settle an invoice
Call settle with the invoice id and amount; the adapter records the settlement
and returns its status.

## Refund
Call refund with the invoice id; only an unpaid invoice can be refunded.

## Errors
A settle on an unknown invoice fails with UNKNOWN_INVOICE; a refund after
payment fails with ALREADY_PAID.

## Worked example
settle("inv-7", 25) returns PAID; a second settle("inv-7", 25) fails with
ALREADY_PAID.

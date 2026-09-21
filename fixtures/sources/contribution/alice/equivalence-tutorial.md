# Choosing an equivalence rule for your first Intelligent Contract

Author wallet: 0x2181588581f943be374fbde775cd83c4c4b2bbcc

When several validators run your contract, each one gets its own answer from
its own model. This tutorial shows how to decide which parts of those answers
must match before the network accepts a result.

## Step 1: find the field that decides what happens
Write down the one field your contract acts on - a verdict, a status, a payout
band. That field is what validators must agree on.

## Step 2: let the explanation vary
Explanations and wording will differ between models. Do not compare them; store
them for humans to read.

## Step 3: test a disagreement
In direct mode, give the validator a leader result with a different verdict and
check that it votes no. If it votes yes, your rule compares too little.

## Try it
Take a contract that stores a review score, compare only the score band, and
watch two differently worded reviews reach the same accepted result.

# Collection kit: write queries in your own words

You are helping measure how well Ibid finds the right law sections when a person describes a case with more than one thing done wrong. Write 20 to 30 queries. Your own wording is the point.

## How to write one query

- Describe the situation as you would to a lawyer you are meeting for the first time.
- Three to eight sentences, at least 20 words.
- Include at least two different things done wrong.
- Real or invented situations are both fine.
- Do not use names, places, dates or phone numbers.
- Do not write section numbers or Act names with numbers ("Section 302", "u/s 420").
- Do not ask an AI to write the query. Queries written by an assistant are refused by the project.

## Three sample shapes

These show the shape only. Write your own facts.

1. A fight and a threat. Two neighbours argue about a shared wall. One hits the other with a stick and the other is hurt. Later, standing outside the house, he says he will come back and finish the job.
2. A deal gone wrong and a forged paper. A man takes money from a buyer to hand over a shop. He shows a stamped paper saying the shop is his, which he had made himself. The shop belongs to someone else and the buyer has lost the money.
3. A family dispute and a death. A husband and his relatives keep demanding more money from the wife's family and harass her at home. One night she is found dead in the house, and her family says she was beaten.

## How to hand them in

Put the queries in `docs/multicharge-queries-template.txt` format: one query per block, blocks separated by a line holding only `---`. Then run:

```bash
uv run ibid charges intake --queries my-queries.txt --author-type owner --author <your label> --out draft-set.json
```

The command refuses an empty block, a block under 20 words, a block with a section number, and a duplicate block, and says which block and why. A draft set has no labels yet and fails `ibid charges validate` until they are added.

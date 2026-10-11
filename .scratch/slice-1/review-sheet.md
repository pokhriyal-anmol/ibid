# Review sheet: slice-1

Check each item against the cited PDF page of the pinned file. Mark pass or fail. Nothing here is verified until you say so.

## section_lookup-1

- category: section_lookup
- query: IPC 171E
- expected: "171E. Punishment for bribery.—Whoever commits the offence of bribery shall be punished with imprisonment of either description for a term which may extend to one year, or with fine, or with both: Provided that bribery by treating shall be punished with fine only. Explanation.—“Treating” means that form of bribery where the gratification consists in food, drink, entertainment, or provision.
- page: IPC 46
- result: [ ] pass  [ ] fail

## section_lookup-8

- category: section_lookup
- query: BNS 271
- expected: "271. Whoever unlawfully or negligently does any act which is, and which he knows or has reason to believe to be, likely to spread the infection of any disease dangerous to life, shall be punished with imprisonment of either description for a term which may extend to six months, or with fine, or with both.
- page: BNS 74
- result: [ ] pass  [ ] fail

## subprovision_lookup-7

- category: subprovision_lookup
- query: IPC 120B(2)
- expected: "(2) Whoever is a party to a criminal conspiracy other than a criminal conspiracy to commit an offence punishable as aforesaid shall be punished with imprisonment of either description for a term not exceeding six months, or with fine or with both.
- page: IPC 35
- result: [ ] pass  [ ] fail

## cross_reference_chain-4

- category: cross_reference_chain
- query: BNS 118(1)
- expected: "118. (1) Whoever, except in the case provided for by sub-section (1) of section 122, voluntarily causes hurt by means of any instrument for shooting, stabbing or cutting, or any instrument which, used as a weapon of offence, is likely to cause death, or by means of fire or any heated substance, or by means of any poison or any corrosive substance, or by means of any explosive substance, or by means of any substance which it is deleterious to the human body to inhale, to swallow, or to receive into the blood, or by means of any animal, shall be punished with imprisonment of either description for a term which may extend to three years, or with fine which may extend to twenty thousand rupees, or with both.
- page: BNS 39
- result: [ ] pass  [ ] fail

## ipc_to_bns-1

- category: ipc_to_bns
- query: IPC 10
- expected: ["BNS 2(19)","BNS 2(35)"]
- type: split
- page: IPC 15 and BNS 4
- result: [ ] pass  [ ] fail

## ipc_to_bns-2

- category: ipc_to_bns
- query: IPC 23
- expected: ["BNS 2(36)","BNS 2(37)","BNS 2(38)"]
- type: split
- page: IPC 18 and BNS 6
- result: [ ] pass  [ ] fail

## ipc_to_bns-3

- category: ipc_to_bns
- query: IPC 54
- expected: ["BNS 5"]
- type: merged
- page: IPC 21 and BNS 8
- result: [ ] pass  [ ] fail

## ipc_to_bns-4

- category: ipc_to_bns
- query: IPC 63
- expected: ["BNS 8"]
- type: merged
- page: IPC 22 and BNS 8
- result: [ ] pass  [ ] fail

## ipc_to_bns-5

- category: ipc_to_bns
- query: IPC 18
- expected: []
- type: removed
- page: IPC 16 and BNS ?
- result: [ ] pass  [ ] fail

## ipc_to_bns-6

- category: ipc_to_bns
- query: IPC 14
- expected: []
- type: removed
- page: IPC 15 and BNS ?
- result: [ ] pass  [ ] fail

## ipc_to_bns-7

- category: ipc_to_bns
- query: IPC 34
- expected: ["BNS 3(5)"]
- type: one-to-one
- page: IPC 19 and BNS 7
- result: [ ] pass  [ ] fail

## bns_to_ipc-1

- category: bns_to_ipc
- query: BNS 111
- expected: []
- type: new
- page: IPC ? and BNS 35
- result: [ ] pass  [ ] fail

## Contested or unjudged (dropped from the drafts)

- concordance IPC 124A-> (removed)
- concordance ->BNS 152 (new)
- gold cross_reference_chain-8: IPC 376C

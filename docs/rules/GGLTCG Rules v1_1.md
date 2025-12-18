# GGLTCG Rules v1.1

*A tactical two-player card game with no randomness in draws—only skill and
strategy.*

## **Quick Rules Summary**

* **Objective:** Put all opponent's cards into their Sleep Zone.
* **Turn Start:** Gain 4 CC (Player 1 on Turn 1 gains only 2).
* **CC:** Use CC to play cards and tussle. Unspent CC are saved for your
  next turn. Max 7 CC per player at any time.
* **Tussle:** Pay CC to have two Toys fight. Higher speed strikes first (turn
  bonus).

***

## **The Golden Rule**

If a card's text contradicts these rules, the card text takes precedence.

***

## **Game Objective**

Win immediately by putting all your opponent's cards into their Sleep Zone.

***

## **Game Components**

* **18 unique cards** (no duplicates)
* **Command Counters (CC)**: The resource for playing cards and tussling
* **Three zones per player**: Hand, In Play, Sleep Zone

***

## **Card Types**

### **Toy**

Cards with three stats: **Speed**, **Strength**, and **Stamina**. Toys are
played into the In Play zone and remain there until sleeped. They can
participate in tussles.

### **Action**

Cards with no stats. When played, an Action resolves its effect immediately,
then moves to your Sleep Zone.

***

## **Setup**

1. Each player selects **6 unique cards** from the 18-card pool (no duplicates
   in your 6).
2. Both players **reveal** their 6 cards to each other.
3. Both players place their 6 cards into their **hand**.
4. Randomly determine who goes first (coin flip, die roll, mutual agreement).
5. The game begins with **no CC** held by either player.

***

## **Game Zones**

### **Hand**

Where you hold cards before playing them. Cards in hand are hidden from your
opponent unless an effect reveals them.

### **In Play**

Where Toys remain after being played. Cards here are considered "awake" and
active.

### **Sleep Zone**

Where cards go when sleeped. Cards here are face-up and visible to both players.

### **Zone Change Reset**

When a card moves between zones, remove all modifications from it (stat changes,
damage, temporary effects). It enters the new zone with its original printed
values.

***

## **Turn Structure**

Each turn has three phases:

### **Phase 1: Start of Turn**

1. Gain **4 CC**. **First Turn Exception**: The starting player gains only **2
   CC** on their first turn (Turn 1).
1. Resolve any "at the start of your turn" effects (none in the current 18-card
   set).

### **Phase 2: Main Phase**

During this phase, you may take any of these actions in any order, as many times
as you can afford:

* **Play a card** from your hand
* **Start a tussle** with one of your Toys
* **Activate abilities** on cards you control (like Archer's Stamina removal)

**Priority**: You (the active player) have priority first. After each action
resolves, you regain priority and may act again. When you're done, pass priority
to your opponent. Your opponent may respond with triggered abilities (like
Beary's tussle cancel) but cannot take other actions unless a card allows it.
When both players pass priority consecutively, move to End Phase.

### **Phase 3: End of Turn**

1. Resolve any "at the end of your turn" effects.
2. **Unspent CC is lost**—it does not carry over to the next turn.
3. Your turn ends; your opponent begins their turn.

***

## **Playing Cards**

### **How to Play a Card**

1. **Announce** the card you're playing from your hand.
2. Make any required choices (e.g., if playing Copy, choose which Toy to copy).
3. Calculate the **total cost** after applying any cost reductions or increases.
4. **Pay the cost** in CC (you can only play a card if you have enough CC).
5. **Resolve the card**: Toys enter In Play awake—their effects work
   immediately; Actions resolve their effect, then move to your Sleep Zone.

### **When Card Text Works**

A card's text only functions while it's in play, **unless** the card
specifically says otherwise.

**Exception in the 18-card set**: Beary can be played from your hand on your
opponent's turn using its own triggered ability.

***

## **Special Card Mechanics**

### **Copy**

* **Printed Cost**: ? (variable)
* **How to Play Copy**:

1. Announce Copy from your hand.
2. Choose a Toy you control that's currently in play.
3. Copy's cost equals the **printed cost** of the chosen Toy.
4. Pay that cost; Copy enters play as an exact duplicate of the chosen Toy (same
   name, stats, text, everything).

* Copy remains a duplicate while in play. If it leaves play (sleeped, returned
  to hand, etc.), it reverts to being "Copy" with cost "?".
* You can have multiple Copies in play, each copying different Toys (or the same
  Toy).

### **Dream**

* **Text**: "This card costs 1 less for each of your sleeping cards."
* Count the number of cards in your Sleep Zone when you announce Dream. Reduce
  Dream's cost by that amount (minimum 0).
* **Example**: Dream's printed cost is 4. If you have 3 cards in your Sleep
  Zone, Dream costs 1 CC.

### **Ballaber**

* **Text**: "You may sleep 1 of your cards to play this card for free."
* You have two payment options:
* **Option A**: Pay Ballaber's printed cost (3 CC) normally.
* **Option B**: Sleep 1 of your cards currently in play (move it to your Sleep
    Zone), then pay 0 CC for Ballaber.
* Ballaber then enters In Play.

### **Rush**

* **Text**: "Gain 2 CC. This card may not be played on your first turn."
* Rush cannot be played on Turn 1 (the starting player's first turn). After Turn
  1, any player may play Rush normally.

***

## **Tussling (Combat)**

### **Starting a Tussle**

Tussling is how you engage your opponent's cards. You may only initiate a tussle
during your turn. The default cost for any tussle is 2 CC, though this can be
modified by card effects (e.g., Wizard, Raggy).

There are two types of tussles, depending on whether your opponent has Toys in
their In-Play zone.

### **Type 1: Standard Tussle (vs. Defender)**

Use this when your opponent has one or more Toys in play.

1. **Declare Tussle:** Choose one of your active Toys (the attacker) and one of
   your opponent's active Toys (the defender).
2. **Pay Cost:** Pay the tussle cost (default 2 CC).
3. **Resolve:** Follow the **Tussle Resolution** steps below.

### **Type 2: Direct Attack (No Defenders)**

Use this when your opponent has **no Toys in play**. You may do this at most
**twice per turn**.

1. **Declare Attack:** Choose one of your active Toys to be the attacker.
2. **Pay Cost:** Pay the tussle cost (default 2 CC).
3. **Target Hand:** Your opponent must have at least one card in their hand.
4. **Resolve:** A random card from your opponent's hand is moved to their Sleep
   Zone; the card is revealed to both players. Important: Cards sleeped from the
   hand this way do **not** trigger their "when sleeped" abilities.

### **Tussle Cost Modifiers**

* **Wizard**: "Your cards' tussles cost 1." If you control Wizard, all your
  tussles cost 1 CC instead of 2.
* **Raggy**: "This card's tussles cost 0." Raggy's tussles cost 0 CC.
* **Restriction**: Raggy cannot tussle on Turn 1 (the starting player's first
    turn).
* Multiple cost modifiers: Use the lowest cost. Modifiers don't stack beyond the
  lowest option (e.g., two Wizards still cost 1 CC per tussle, not 0).

### **Tussle Cancellation (Beary)**

* **Beary**: "When your opponent tussles, you may play this card, the tussle is
  cancelled."
* **Timing**: After your opponent declares a tussle and pays the tussle cost,
  you may play Beary from your hand (paying Beary's 1 CC cost).
* **Effect**: The tussle is cancelled—no strikes occur, no damage is dealt.
  Beary enters play. **Your opponent does not get their tussle cost refunded.**
* Your opponent may then take another action.

### **Tussle Resolution**

* **Calculate Speed**: Apply all modifiers to both Toys' Speed.
* **Turn Bonus**: During your turn, your Toys have **+1 Speed** for tussles.
* Apply buffs from cards like Ka (+2 Strength) or Demideca (+1 to all stats).
* **Determine Strike Order**:
* **Higher Speed strikes first**. If that first strike reduces the defender to
    0 or fewer Stamina, the defender is sleeped immediately and does **not**
    strike back.
* **Tied Speed**: Both Toys strike simultaneously.
* **Resolve Strikes**:
* Each striking Toy deals damage equal to its **Strength** to the opposing
    Toy's **Stamina**.
* Reduce the opposing Toy's Stamina by the attacking Toy's Strength.
* **Sleep Check**: After all strikes, if any Toy has Stamina ≤ 0, that Toy is
  **sleeped** (moved to its owner's Sleep Zone).

### **Direct Attack (No Defenders)**

If your opponent has **no Toys in play** when you start a tussle:

1. Choose one of your Toys in play.
2. Pay the tussle cost (default 2 CC, modified by Wizard/Raggy).
3. **Sleep a random card from your opponent's hand**:
    * If your opponent has N cards in hand, generate a random number from 1 to
      N.
    * Sleep the card at that position.
    * Reveal the sleeped card to both players.
4. This counts as a tussle for cost purposes.
5. You may do this **at most twice per turn**.
6. Your opponent must have at least one card in hand; if their hand is empty,
   you cannot make a direct attack.

**Important**: Cards sleeped from hand do **not** trigger "when sleeped"
abilities.

***

## **Sleeping and Unsleeping**

### **How Cards Become Sleeped**

A card is **sleeped** (moved to its owner's Sleep Zone) when:

* A Toy's Stamina is reduced to 0 or less (automatic).
* An effect specifically sleeps it (Clean, Snuggles, direct attack).
* It's an Action that has finished resolving.

### **"When Sleeped" Triggers**

Triggered abilities that say "when sleeped" (Umbruh, Snuggles) only activate if
the card was **in play** when it became sleeped.

* Cards sleeped from hand (via direct attack) do **not** trigger these
  abilities.
* Cards returned to hand (via Toynado) do **not** trigger these abilities
  because they weren't sleeped.

### **Unsleep**

"Unsleep" means to return a card from your Sleep Zone to your hand.

* **Wake**: "Unsleep 1 of your cards." Choose 1 card in your Sleep Zone and
  return it to your hand.
* **Sun**: "Unsleep 2 of your cards." Choose up to 2 cards in your Sleep Zone
  and return them to your hand.

***

## **Command Counters (CC)**

### **Gaining CC**

* At the start of your turn: Gain 4 CC (2 CC on Turn 1 for the starting player).
* From card effects:
* **Umbruh**: "When sleeped, gain 1 CC."
* **Rush**: "Gain 2 CC."

### **Spending CC**

* Playing cards (pay the card's cost).
* Starting tussles (default 2 CC, modified by Wizard/Raggy).
* Activating abilities (Archer: 1 CC per 1 Stamina removed).

### **Payment Rules**

* You can only announce an action if you can pay its full cost.
* Apply cost reductions when calculating cost, before payment.

### **CC End of Turn & Maximum Cap**

* **Banking CC:** Unspent Command Counters are not lost at the end of your turn.
  They are saved for your next turn.
* **Maximum Cap:** A player can hold a maximum of 7 CC at any time. If gaining
  CC would cause your total to exceed 7, you only gain enough to reach the cap
  of 7.
* *Example: If you have 5 CC at the start of your turn, you will only gain 2 CC
  (to reach the maximum of 7), instead of the usual 4.*

***

## **Card Effects**

### **Continuous Effects**

Some Toys have effects that apply as long as they're in play:

* **Ka**: "Your cards have +2 Strength."
* **Demideca**: "Your cards have +1 of all stats" (+1 Speed, +1 Strength, +1
  Stamina).
* **Wizard**: "Your cards' tussles cost 1."

**Stacking**: If you have multiple copies of the same continuous effect, they
stack additively.

* **Example**: 2 Ka in play give your cards +4 Strength total.

When a card providing a continuous effect leaves play, immediately recalculate
all affected cards.

### **Triggered Abilities**

Triggered abilities activate when their condition is met (e.g., "when sleeped,"
"when your opponent tussles").

* **Optional** triggers use "may"—you choose whether to use them (Beary,
  Snuggles).
* **Mandatory** triggers have no "may"—they must resolve (Umbruh).

### **Activated Abilities**

**Archer**: "You may spend CC to remove Stamina from cards."

* During your Main Phase, pay 1 CC to remove 1 Stamina from any Toy in play
  (yours or your opponent's).
* You can repeat this as many times as you can afford.
* This Stamina removal is not damage—it's direct stat reduction.
* If this reduces a Toy to 0 or fewer Stamina, that Toy is sleeped immediately.
* **Archer restriction**: "This card can't start tussles." Archer cannot be
  declared as an attacker in a tussle.

### **Protection Abilities**

**Knight**: "Your opponent's cards' effects don't affect this card."

* Knight ignores all effects from cards your opponent controls (targeting
  effects, stat debuffs, abilities).
* **Exception**: Tussle damage from Strength is not an "effect"—Knight can still
  take damage in tussles.
* Your opponent's Archer cannot target your Knight. Your own Archer can target
  your own Knight.
* **Conditional Win**: "On your turn, this card wins all tussles it enters."
* When Knight tussles on your turn, it automatically sleeps the opposing Toy
    (no matter the stats).
* The opposing Toy does not strike back.
* On your opponent's turn, Knight tussles normally (no auto-win).
* **Exception**: Doesn't work against Beary (see below).

**Beary**: "Knight's effects don't affect this card."

* Beary ignores all effects from cards named "Knight."
* Knight's conditional win ability does not work against Beary—they tussle
  normally.

***

## **Advanced Rules**

### **State-Based Actions**

These are automatic checks that happen constantly:

* **Zero Stamina**: If a Toy has Stamina ≤ 0, it's sleeped immediately.
* **Victory Check**: If all your opponent's cards are in their Sleep Zone, you
  win immediately.

### **Ownership and Control**

* **Ownership never changes**. Each card has one owner (the player who started
  with it).
* **Control** can change via effects.
* **Twist**: "Put a card your opponent has in play in play, but under your
    control."
* Choose an opposing Toy in play. It switches to your side (you now control
    it).
* Ownership is unchanged. If it leaves play, it goes to its owner's Sleep Zone
    or hand (your opponent's).
* **Toynado**: "Put all cards that are in play into their owner's hands."
* All Toys return to their **owners' hands** (not controllers').
* No "when sleeped" triggers occur (cards aren't sleeped, they're returned).

### **Targeting**

* When an effect requires you to choose or target a card, declare it when you
  play the effect.
* Targets must be legal when announced and when the effect resolves.
* If a target becomes illegal (leaves play, gains protection), that part of the
  effect does nothing.

### **Infinite Loops**

* **Optional Loops**: If you could repeat an optional action endlessly (e.g.,
  Archer with infinite CC), you must choose a finite number of repetitions, then
  take a different action or pass priority.
* **Mandatory Loops**: None exist in the current 18-card set.

***

## **Quick Reference**

### **Turn Sequence**

1. **Start**: Gain 4 CC (2 on Turn 1 for starting player).
2. **Main**: Play cards, tussle, activate abilities.
3. **End**: Unspent CC is lost. Turn passes.

### **Tussle Steps**

1. Declare attacker and target.
2. Check for Beary interrupt (opponent can play Beary to cancel).
3. Pay tussle cost.
4. Calculate Speed (include turn bonus and buffs).
5. Higher Speed strikes first; tied Speed strikes simultaneously.
6. Apply damage (Strength reduces opponent's Stamina).
7. Sleep any Toy with Stamina ≤ 0.

### **Key Interactions**

* **Knight's auto-win**: Only on your turn; doesn't work vs. Beary.
* **"When sleeped" triggers**: Only if the card was in play when sleeped.
* **Toynado**: Returns all Toys to owners' hands (not sleeped; no triggers).
* **Copy**: Costs the same as the Toy you're copying; becomes an exact
  duplicate.
* **Direct attacks**: Sleep a random card from opponent's hand when they have no
  Toys in play (max 2/turn).

***

## **Glossary**

**Action**: Card type with no stats. Resolves its effect when played, then
becomes sleeped.

**Activated Ability**: An ability you can use by paying a cost (Archer's Stamina
removal).

**Active Player**: The player whose turn it is.

**Awake**: A Toy that's in play (not sleeped).

**CC (Command Counters)**: The resource for playing cards, tussling, and
abilities. Gain 4 per turn (2 on Turn 1 for starting player).

**Control**: The player who makes decisions for a card. Can change via Twist.

**Continuous Effect**: An effect that applies while its source is in play (Ka,
Wizard, Demideca).

**Direct Attack**: A tussle when your opponent has no Toys in play. Sleeps a
random card from their hand (max 2/turn).

**Effect**: Text on a card that does something. Does not include tussle damage.

**Hand**: Zone where you hold cards before playing them. Start with 6 cards.

**In Play**: Zone where Toys remain until sleeped.

**Owner**: The player who started with a card. Never changes.

**Priority**: Permission to take actions. Active player has priority first in
Main Phase.

**Protection**: Immunity to effects from specific sources (Knight, Beary).

**Sleep**: To move a card to its owner's Sleep Zone.

**Sleeped**: State of being in the Sleep Zone; also the event of becoming
sleeped.

**Sleep Zone**: Where cards go when sleeped. Face-up and visible to both
players.

**Speed**: Stat determining strike order in tussles. Higher Speed strikes first.

**Stamina**: Stat representing a Toy's durability. When Stamina reaches 0, the
Toy is sleeped.

**State-Based Action**: Automatic check (0 Stamina → sleep, all opponent cards
sleeped → you win).

**Strength**: Stat determining how much damage a Toy deals in tussles.

**Strike**: The moment a Toy deals damage equal to its Strength during a tussle.

**Target**: A card chosen for an effect.

**Toy**: Card type with Speed, Strength, and Stamina. Remains in play until
sleeped.

**Trigger**: An ability that activates when a condition is met ("when sleeped,"
"when your opponent tussles").

**Turn 1**: The starting player's first turn. They gain 2 CC (not 4).

**Tussle**: Combat between two Toys. Default cost 2 CC.

**Unsleep**: Return a card from your Sleep Zone to your hand.

**Zone**: A game area (Hand, In Play, Sleep Zone).

***

## **Card List (18 Cards)**

### **Toys (11)**

Archer, Ballaber, Beary, Demideca, Dream, Ka, Knight, Raggy, Snuggles, Umbruh,
Wizard

### **Actions (7)**

Clean, Copy, Rush, Sun, Toynado, Twist, Wake

***

## End of GGLTCG Rules v1.0

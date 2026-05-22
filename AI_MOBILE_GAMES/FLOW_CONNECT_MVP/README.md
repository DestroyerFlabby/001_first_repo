# Number Hex MVP

Godot 4.2+ mobile puzzle prototype.

## Current Gameplay

- Hexagon-shaped board made of equal hex tiles.
- Each level contains numbers `1` through `10`.
- Start at `1` and draw one continuous path through `2`, `3`, `4`, and onward to `10`.
- The path can move only to adjacent hex tiles.
- The path cannot overlap itself.
- `R` resets the current level.
- `Esc` returns to the home screen.

## Content

The MVP currently includes 10 solvable levels generated from known non-overlapping solution paths:

```text
data/level_data.gd
```

## Run

Open this folder in Godot:

```text
AI_MOBILE_GAMES/FLOW_CONNECT_MVP
```

Then press Play.


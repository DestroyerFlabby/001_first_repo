---
name: mobile-game-builder
description: Build, prototype, or plan AI-assisted mobile video games. Use when Codex is asked to create mobile game concepts, game loops, mechanics, monetization plans, Unity/Godot/web mobile prototypes, AI-generated asset plans, app store metadata, or production checklists for mobile games.
---

# Mobile Game Builder

## Core Workflow

Start by identifying:

- Platform target: iOS, Android, or both.
- Engine path: Unity, Godot, React Native, Flutter, or mobile web.
- Primary input: tap, swipe, drag, tilt, or simple virtual controls.
- Session length: hyper-casual, casual, mid-core, or long-form.
- Core loop: action, reward, progression, difficulty escalation, and return reason.
- Monetization: paid, ads, in-app purchases, subscriptions, or no monetization.

If the user has not chosen an engine, recommend the simplest viable option:

- Use Unity for ad-monetized 2D/3D mobile games with broad plugin support.
- Use Godot for lightweight 2D games and open-source workflows.
- Use web tech when the fastest playable prototype matters more than native store readiness.

## Prototype Standards

When building a prototype:

- Make the first screen playable, not a landing page.
- Prioritize the core loop over menus, account systems, or store polish.
- Use responsive touch-friendly controls.
- Keep assets replaceable and organized by role.
- Add a short README that explains how to run the prototype.
- Verify the game on a mobile-sized viewport or emulator when possible.

## AI Asset Workflow

For generated assets, define:

- Art style and camera perspective.
- Sprite or model dimensions.
- Background transparency needs.
- Animation states.
- Export format.
- Licensing and attribution notes if assets come from external sources.

Prefer repo-native assets for code-driven prototypes. Use generated bitmap assets when visual style, characters, environments, icons, or store creatives are part of the task.

## Production Checklist

Before treating a prototype as production-ready, check:

- Performance on target devices.
- Touch ergonomics.
- Pause, resume, and interruption behavior.
- Save state.
- Privacy policy needs.
- App store content rating.
- Analytics events.
- Crash reporting.
- Ad network or payment SDK compliance.
- Store screenshots, icon, description, and keywords.


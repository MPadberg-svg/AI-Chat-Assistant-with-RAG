## What changed

<!-- A short description of the change and the problem it solves. -->

## Why

<!-- Link the issue this closes, or explain the motivation. -->

Closes #

## How it was verified

<!-- Check what applies and add details. -->

- [ ] `black --check app tests` and `flake8 app tests`
- [ ] `pytest -q` (new/updated tests included)
- [ ] `npm run lint`, `npm run format:check`, `npm test`
- [ ] `npm run build`
- [ ] Manually exercised the affected endpoint or UI

## Checklist

- [ ] No secrets, API keys or `.env` files committed
- [ ] Behaviour changes are covered by tests
- [ ] Documentation updated (README / CHANGELOG) where relevant
- [ ] `__version__` bumped if this should cut a minor or major release

## Screenshots / logs

<!-- For UI changes, before/after screenshots help a lot. -->

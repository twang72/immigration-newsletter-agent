# immigration newsletter agent

Autonomous agents that generate income while you sleep — no client involvement required.

## Modules

### `/newsletter`
Monitors immigration policy changes (IRCC, USCIS), auto-writes and sends a weekly newsletter via Beehiiv. Monetized via sponsorships and Beehiiv boosts.

### `/digital-products`
Auto-generates niche immigration guides and checklists. Lists and sells them on Gumroad. Agent monitors trending topics and creates new products automatically.

### `/shared`
Shared utilities: Claude API client, content generation helpers, scheduling.

## Stack
- **AI**: Claude API (claude-sonnet-4-6)
- **Newsletter**: Beehiiv API
- **Digital Products**: Gumroad API
- **Scheduler**: GitHub Actions (cron)
- **Language**: Python

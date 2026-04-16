const tierStyles: Record<string, string> = {
  platinum: 'bg-tier-platinum/15 text-tier-platinum border-tier-platinum/30',
  gold: 'bg-tier-gold/15 text-tier-gold border-tier-gold/30',
  silver: 'bg-tier-silver/15 text-tier-silver border-tier-silver/30',
  bronze: 'bg-tier-bronze/15 text-tier-bronze border-tier-bronze/30',
}

export function TierBadge({ tier }: { tier: string }) {
  const style = tierStyles[tier] || tierStyles.bronze
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${style}`}>
      {tier}
    </span>
  )
}

function tallyGroups(count) {
  const groups = []
  let remaining = count
  while (remaining > 0) {
    groups.push(Math.min(remaining, 5))
    remaining -= 5
  }
  return groups
}

/**
 * @param {{ count: number }} props
 */
export default function TallyMarks({ count }) {
  return (
    <span aria-hidden="true" className="inline-flex gap-1.5 font-data text-ink">
      {tallyGroups(count).map((size, groupIndex) => (
        <span key={groupIndex} className="inline-flex">
          {Array.from({ length: size }, (_, strokeIndex) => (
            <span key={strokeIndex} className={strokeIndex > 0 ? 'ml-0.5' : ''}>
              {size === 5 && strokeIndex === 4 ? '⟍' : '⟋'}
            </span>
          ))}
        </span>
      ))}
    </span>
  )
}

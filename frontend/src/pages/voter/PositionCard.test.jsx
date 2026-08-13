import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import PositionCard from './PositionCard'

const position = {
  id: 3,
  title: 'Senator',
  max_votes: 2,
  candidates: [
    { id: 11, full_name: 'Nora Reyes', student_number: '2021-001', platform: '' },
    { id: 12, full_name: 'Ben Cruz', student_number: '2021-002', platform: '' },
    { id: 13, full_name: 'Amy Lim', student_number: '2021-003', platform: '' },
  ],
}

const singlePosition = {
  id: 4,
  title: 'President',
  max_votes: 1,
  candidates: [
    { id: 21, full_name: 'Nora Reyes', student_number: '2021-001', platform: '' },
    { id: 22, full_name: 'Ben Cruz', student_number: '2021-002', platform: '' },
  ],
}

describe('PositionCard max_votes enforcement', () => {
  it('renders checkboxes and allows selecting up to max_votes candidates', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<PositionCard position={position} selectedIds={[]} onChange={onChange} />)

    await user.click(screen.getByRole('checkbox', { name: /Nora Reyes/ }))
    expect(onChange).toHaveBeenCalledWith([11])
  })

  it('disables unselected checkboxes once the max_votes limit is reached, with an explanation', () => {
    render(<PositionCard position={position} selectedIds={[11, 12]} onChange={vi.fn()} />)

    const untouched = screen.getByRole('checkbox', { name: /Amy Lim/ })
    expect(untouched).toBeDisabled()
    expect(screen.getByText(/maximum of 2/i)).toBeInTheDocument()
  })

  it('still allows unchecking a selected candidate while at the limit', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<PositionCard position={position} selectedIds={[11, 12]} onChange={onChange} />)

    const selected = screen.getByRole('checkbox', { name: /Ben Cruz/ })
    expect(selected).not.toBeDisabled()
    await user.click(selected)
    expect(onChange).toHaveBeenCalledWith([11])
  })

  it('renders radios for a max_votes of 1 and swaps selection instead of accumulating', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<PositionCard position={singlePosition} selectedIds={[21]} onChange={onChange} />)

    await user.click(screen.getByRole('radio', { name: /Ben Cruz/ }))
    expect(onChange).toHaveBeenCalledWith([22])
  })

  it('offers an explicit Clear selection action for single-choice positions', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<PositionCard position={singlePosition} selectedIds={[21]} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: /clear selection/i }))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('shows the selection count against the limit', () => {
    render(<PositionCard position={position} selectedIds={[11]} onChange={vi.fn()} />)
    expect(screen.getByText('1/2')).toBeInTheDocument()
  })
})

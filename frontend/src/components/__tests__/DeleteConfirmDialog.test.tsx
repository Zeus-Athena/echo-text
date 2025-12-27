import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import '@testing-library/jest-dom'
import { DeleteConfirmDialog } from '../DeleteConfirmDialog'

describe('DeleteConfirmDialog', () => {
    it('renders correctly when open', () => {
        const onClose = vi.fn()
        const onConfirm = vi.fn()

        render(
            <DeleteConfirmDialog
                isOpen={true}
                onClose={onClose}
                onConfirm={onConfirm}
                title="Custom Title"
                description="Custom Description"
            />
        )

        expect(screen.getByText('Custom Title')).toBeInTheDocument()
        expect(screen.getByText('Custom Description')).toBeInTheDocument()
        expect(screen.getByText('确认删除')).toBeInTheDocument()
        expect(screen.getByText('取消')).toBeInTheDocument()
    })

    it('does not render when closed', () => {
        const onClose = vi.fn()
        const onConfirm = vi.fn()

        render(
            <DeleteConfirmDialog
                isOpen={false}
                onClose={onClose}
                onConfirm={onConfirm}
            />
        )

        expect(screen.queryByText('确认删除')).not.toBeInTheDocument()
    })

    it('calls onConfirm when confirm button clicked', () => {
        const onClose = vi.fn()
        const onConfirm = vi.fn()

        render(
            <DeleteConfirmDialog
                isOpen={true}
                onClose={onClose}
                onConfirm={onConfirm}
            />
        )

        // There are two "确认删除" texts: one in title, one in button.
        // We want to click the button.
        const buttons = screen.getAllByRole('button')
        const confirmBtn = buttons[1] // The second button is the confirm button

        fireEvent.click(confirmBtn)
        expect(onConfirm).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when cancel button clicked', () => {
        const onClose = vi.fn()
        const onConfirm = vi.fn()

        render(
            <DeleteConfirmDialog
                isOpen={true}
                onClose={onClose}
                onConfirm={onConfirm}
            />
        )

        fireEvent.click(screen.getByText('取消'))
        expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('shows loading state properly', () => {
        render(
            <DeleteConfirmDialog
                isOpen={true}
                onClose={vi.fn()}
                onConfirm={vi.fn()}
                isLoading={true}
            />
        )

        // Check that the button no longer contains the text "确认删除"
        // Use getAllByRole to find buttons, and since we know there are 2, the second is confirm
        const buttons = screen.getAllByRole('button')
        // Ensure we found both
        expect(buttons).toHaveLength(2)

        buttons.forEach(btn => expect(btn).toBeDisabled())

        const confirmBtn = buttons[1] // The second button is the confirm button

        expect(confirmBtn).toBeDisabled()
        expect(confirmBtn).not.toHaveTextContent('确认删除')
        // We can check for inner HTML to confirm the spinner, although checking text content is sufficient given it replaces the text
    })
})

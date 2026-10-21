import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QuestionForm } from './QuestionForm';
import type { Skill } from '@/types';

const skills: Skill[] = [{ id: 1, name: 'Logic', description: null, category_id: 1, category_name: 'Aptitude' }];

function setup() {
  const onSubmit = vi.fn();
  render(<QuestionForm skills={skills} submitting={false} onSubmit={onSubmit} onCancel={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Question'), { target: { value: 'What is 2+2?' } });
  fireEvent.change(screen.getByLabelText('Skill'), { target: { value: '1' } });
  return onSubmit;
}

describe('QuestionForm validation', () => {
  it('requires at least 2 options with text', () => {
    const onSubmit = setup();
    fireEvent.change(screen.getByLabelText('Option 1 text'), { target: { value: '4' } });
    fireEvent.click(screen.getByLabelText('Option 1 is correct'));
    fireEvent.click(screen.getByRole('button', { name: 'Add question' }));
    expect(screen.getByText('Provide at least 2 options with text.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('requires at least 1 correct option', () => {
    const onSubmit = setup();
    fireEvent.change(screen.getByLabelText('Option 1 text'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Option 2 text'), { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add question' }));
    expect(screen.getByText('Mark at least 1 correct option.')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits a valid question', () => {
    const onSubmit = setup();
    fireEvent.change(screen.getByLabelText('Option 1 text'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Option 2 text'), { target: { value: '5' } });
    fireEvent.click(screen.getByLabelText('Option 1 is correct'));
    fireEvent.click(screen.getByRole('button', { name: 'Add question' }));
    expect(onSubmit).toHaveBeenCalledWith({
      skill_id: 1,
      difficulty: 'MEDIUM',
      body: 'What is 2+2?',
      options: [
        { id: 'a', text: '4' },
        { id: 'b', text: '5' },
      ],
      correct_option_ids: ['a'],
      marks: 1,
    });
  });
});

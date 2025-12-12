import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedApi = { get: jest.fn(), post: jest.fn() };

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(() => ({
      matches: false,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

beforeEach(() => {
  localStorage.clear();
  mockedApi.get.mockReset();
  mockedApi.post.mockReset();
  mockedAxios.create.mockReturnValue(mockedApi as any);
  mockedApi.get.mockResolvedValue({ data: { type: 'manual_ui', prompt: 'ORIGINAL PROMPT' } });
});

test('edits builtin prompt and resets to default', async () => {
  const App = (await import('./App')).default;

  render(<App />);

  const manageButton = await screen.findByTitle(/Управление сценариями/i);
  await userEvent.click(manageButton);

  const manualItem = await screen.findByText(/Ручные тесты — UI Калькулятор/i);
  await userEvent.click(manualItem);

  const promptField = await screen.findByLabelText(/Промпт/i);
  await waitFor(() => expect(promptField).toHaveValue('ORIGINAL PROMPT'));

  await userEvent.clear(promptField);
  await userEvent.type(promptField, 'EDITED PROMPT');

  const saveButton = screen.getByRole('button', { name: /Сохранить/i });
  await userEvent.click(saveButton);

  await waitFor(() => {
    const saved = JSON.parse(localStorage.getItem('edited_builtin_prompts') || '[]');
    const edited = saved.find((p: any) => p.type === 'manual_ui');
    expect(edited?.prompt).toBe('EDITED PROMPT');
  });

  await userEvent.click(screen.getByText(/Ручные тесты — UI Калькулятор/i));

  mockedApi.get.mockResolvedValue({ data: { type: 'manual_ui', prompt: 'ORIGINAL PROMPT' } });
  const resetButton = await screen.findByRole('button', { name: /По умолчанию/i });
  await userEvent.click(resetButton);

  await waitFor(() => {
    const saved = JSON.parse(localStorage.getItem('edited_builtin_prompts') || '[]');
    expect(saved.length).toBe(0);
  });

  await waitFor(() => expect(screen.getByLabelText(/Промпт/i)).toHaveValue('ORIGINAL PROMPT'));
});


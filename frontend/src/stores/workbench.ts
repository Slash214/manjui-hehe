import { create } from 'zustand';
type State = {
  pending: Record<string, string>;
  mark: (key: string, value: string) => void;
  clear: (key: string) => void;
};
export const useWorkbench = create<State>((set) => ({ pending: {},
  mark: (key, value) => set(s => ({pending: {...s.pending, [key]: value}})),
  clear: key => set(s => {const pending = {...s.pending}; delete pending[key]; return {pending};}),
}));

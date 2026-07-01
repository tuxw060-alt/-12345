/** Global app state with Zustand. */

import { create } from 'zustand'
import type { Client } from '../types/invoice'

interface AppState {
  currentClient: Client | null
  setCurrentClient: (client: Client | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentClient: null,
  setCurrentClient: (client) => set({ currentClient: client }),
}))

/** Global app state with Zustand. */

import { create } from 'zustand'
import type { Client } from '../types/invoice'

interface AppState {
  currentClient: Client | null
  clientRefreshKey: number
  setCurrentClient: (client: Client | null) => void
  requestClientRefresh: () => void
}

export const useAppStore = create<AppState>((set) => ({
  currentClient: null,
  clientRefreshKey: 0,
  setCurrentClient: (client) => set({ currentClient: client }),
  requestClientRefresh: () => set((state) => ({ clientRefreshKey: state.clientRefreshKey + 1 })),
}))

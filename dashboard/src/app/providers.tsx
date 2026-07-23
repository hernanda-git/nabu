'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { WebSocketProvider } from '@/components/providers/WebSocketProvider'
import { ThemeProvider } from '@/components/providers/ThemeProvider'

interface NabuProviderProps {
  children: ReactNode
}

export function NabuProvider({ children }: NabuProviderProps) {
  return (
    <ThemeProvider>
      <WebSocketProvider>
        {children}
      </WebSocketProvider>
    </ThemeProvider>
  )
}
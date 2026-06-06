export interface ChartColors {
  grid: string
  axis: string
  tooltipBg: string
  tooltipBorder: string
  text: string
  accent: string
  accent2: string
  lime: string
  green: string
  muted: string
}

export function chartColors(theme: 'dark' | 'light'): ChartColors {
  const dark = theme === 'dark'
  return {
    grid: dark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.08)',
    axis: dark ? '#8b93a7' : '#5d6782',
    tooltipBg: dark ? 'rgba(14,17,26,0.96)' : 'rgba(255,255,255,0.98)',
    tooltipBorder: dark ? 'rgba(255,255,255,0.12)' : 'rgba(15,23,42,0.12)',
    text: dark ? '#eef1f8' : '#0c1322',
    accent: '#5b8cff',
    accent2: '#38e1c6',
    lime: '#c3f53b',
    green: '#4ade80',
    muted: dark ? '#8b93a7' : '#5d6782',
  }
}

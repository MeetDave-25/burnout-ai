/** Business details shown in legal pages and the footer. Set them in frontend/.env before launch. */
export const SITE = {
  company: import.meta.env.VITE_COMPANY_NAME || 'BurnoutAI',
  contactEmail: (import.meta.env.VITE_CONTACT_EMAIL as string | undefined) || '',
  jurisdiction: import.meta.env.VITE_JURISDICTION || 'India',
  updated: '2 October 2026',
}

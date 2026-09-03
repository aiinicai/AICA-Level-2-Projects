import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { GoogleGenAI } from '@google/genai'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    server: {
      watch: {
        ignored: ['**/*.xlsx', '**/*.xls', '**/*.csv', '**/*.pdf', '**/node_modules/**', '**/.git/**']
      }
    },
    plugins: [
      react(),
      {
        name: 'api-cfo-memo-middleware',
        configureServer(server) {
          server.middlewares.use('/api/cfo-memo', async (req, res) => {
            if (req.method !== 'POST') {
              res.statusCode = 405
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ error: 'Method Not Allowed' }))
              return
            }

            let body = ''
            req.on('data', chunk => {
              body += chunk
            })
            req.on('end', async () => {
              try {
                const parsed = JSON.parse(body || '{}')
                const { prompt, company, metrics, periodId } = parsed
                const apiKey = env.GEMINI_API_KEY || process.env.GEMINI_API_KEY

                if (!apiKey) {
                  res.statusCode = 503
                  res.setHeader('Content-Type', 'application/json')
                  res.end(
                    JSON.stringify({
                      success: false,
                      fallback: true,
                      error: 'Server GEMINI_API_KEY environment variable is not configured.'
                    })
                  )
                  return
                }

                const ai = new GoogleGenAI({ apiKey })
                const activeCompanyName = company?.name || 'Active Enterprise';
                const activeCompanyTicker = company?.ticker || company?.nseCode || 'N/A';
                const activeCompanyBse = company?.bseCode || 'N/A';

                const contextData = `
ACTIVE SESSION ENTERPRISE CONTEXT:
• Name: ${activeCompanyName} (${activeCompanyTicker} / BSE: ${activeCompanyBse})
• Sector: ${company?.sector || 'General Industrials'}
• Period: ${periodId || 'Latest'}
• Revenue: ₹ ${metrics?.revenue || company?.salesLatestQuarter || 0} Cr
• Operating EBITDA: ₹ ${metrics?.ebitda || company?.ebitdaLatestQuarter || 0} Cr (OPM: ${metrics?.opmPercent || company?.ebitdaMargin || 0}%)
• Profit After Tax (PAT): ₹ ${metrics?.pat || company?.netProfitLatestQuarter || 0} Cr
• Total Debt: ₹ ${metrics?.totalDebt || company?.debt || 0} Cr
• Net Worth: ₹ ${metrics?.netWorth || company?.netWorth || 0} Cr
• Debt-to-Equity: ${metrics?.debtToEquity || company?.debtToEquity || 0}x
• Interest Coverage Ratio: ${metrics?.interestCoverage || company?.interestCoverage || 0}x
• ROCE %: ${metrics?.rocePercent || company?.roce || 0}%
• Negative Operating Scissors: ${metrics?.hasNegativeScissors || company?.hasOperatingScissors ? 'YES' : 'NO'}
`

                const fullPrompt = `You are an elite, executive-level Chief Financial Officer (CFO) and strategic corporate finance advisor.
Analyze the following corporate financial data and answer the user query with rigorous precision, strategic boardroom clarity, and actionable recommendations.

${contextData}

CRITICAL ENTITY INTEGRITY & CONTEXT RULES:
1. The quantitative financial data above belongs EXCLUSIVELY to "${activeCompanyName}" (${activeCompanyTicker}).
2. CHECK USER QUERY INTENT: Inspect whether the user is explicitly asking to analyze a DIFFERENT company/entity (e.g. asking about "Reliance Industries", "Tata Motors", "TCS", "HDFC Bank", "Infosys", etc.) when the currently selected entity is "${activeCompanyName}".
3. If the user explicitly asks to analyze or review a DIFFERENT company than "${activeCompanyName}":
   - NEVER attribute the financial metrics (Revenue, EBITDA, Debt, OPM, ROCE) of "${activeCompanyName}" to the other company.
   - Begin your response with a clear Entity Mismatch Notice:
     "⚠️ **Entity Context Notice**: The currently active company in this dashboard session is **${activeCompanyName} (${activeCompanyTicker})**. The financial metrics and balance sheet in current session context belong to **${activeCompanyName}**."
   - Advise the user to select the requested company from the company selector dropdown in the top navigation bar to load its verified multi-period Ind-AS financial statements.
   - If you provide any general commentary about the requested company, explicitly state that it is qualitative/external knowledge and that quantitative metrics in the dashboard are currently reflecting **${activeCompanyName}**.
4. If the user query is about "${activeCompanyName}" (or general financial concepts like "What is our debt servicing capacity?", "Analyze our operating scissors", "How can we improve ROCE?"):
   - Proceed with an exhaustive, data-grounded CFO analysis using the provided metrics.

USER QUERY:
${prompt}`

                let responseText = ''

                try {
                  const response = await ai.models.generateContent({
                    model: 'gemini-3.7-flash',
                    contents: fullPrompt
                  })
                  responseText = response.text || ''
                } catch (genErr: any) {
                  console.warn('Dev server gemini-3.7-flash failed, using fallback:', genErr?.message)
                  const fallbackResponse = await ai.models.generateContent({
                    model: 'gemini-3.5-flash-lite',
                    contents: fullPrompt
                  })
                  responseText = fallbackResponse.text || ''
                }

                res.statusCode = 200
                res.setHeader('Content-Type', 'application/json')
                res.end(
                  JSON.stringify({
                    success: true,
                    text: responseText || 'No response text generated.'
                  })
                )
              } catch (err: any) {
                console.error('Dev server Gemini API error:', err)
                res.statusCode = 500
                res.setHeader('Content-Type', 'application/json')
                res.end(
                  JSON.stringify({
                    success: false,
                    fallback: true,
                    error: err.message || 'Internal server error during Gemini inference'
                  })
                )
              }
            })
          })

          server.middlewares.use('/api/auth-proxy', async (req, res) => {
            if (req.method !== 'POST') {
              res.statusCode = 405
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ error: 'Method Not Allowed' }))
              return
            }

            let body = ''
            req.on('data', chunk => {
              body += chunk
            })
            req.on('end', async () => {
              try {
                const parsed = JSON.parse(body || '{}')
                const { email, password } = parsed

                if (!email || !password) {
                  res.statusCode = 400
                  res.setHeader('Content-Type', 'application/json')
                  res.end(JSON.stringify({ error: 'Email and password are required' }))
                  return
                }

                const rawUrl = (env.VITE_SUPABASE_URL || process.env.VITE_SUPABASE_URL || 'https://omybszbzealjvaltzvpi.supabase.co').trim()
                const rawKey = (
                  env.VITE_SUPABASE_PUBLISHABLE_KEY ||
                  process.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
                  'sb_publishable_eujc45-UUKFqGPabJx6cvw_vOCSMBCy'
                ).trim()

                const supabaseUrl = rawUrl.replace(/\/+$/, '')
                const supabaseKey = rawKey
                const endpoint = `${supabaseUrl}/auth/v1/token?grant_type=password`

                const proxyRes = await fetch(endpoint, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'apikey': supabaseKey,
                    'Authorization': `Bearer ${supabaseKey}`
                  },
                  body: JSON.stringify({
                    email: email.trim(),
                    password
                  })
                })

                const data = await proxyRes.json().catch(() => ({}))
                res.statusCode = proxyRes.status
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify(data))
              } catch (proxyErr: any) {
                console.error('Dev server Auth proxy error:', proxyErr?.message)
                res.statusCode = 500
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify({ error: 'Internal Server Error', message: proxyErr?.message }))
              }
            })
          })
        }
      }
    ]
  }
})

import { streamText, convertToModelMessages, createUIMessageStream, createUIMessageStreamResponse, UIMessage } from 'ai'
import { createGoogleGenerativeAI } from '@ai-sdk/google'
import { ENDPOINTS } from '@/lib/api-config'

export const maxDuration = 30

const googleApiKey = process.env.GOOGLE_GENERATIVE_AI_API_KEY || process.env.GOOGLE_API_KEY

export async function POST(req: Request) {
  const { messages, machineContext }: { messages: UIMessage[]; machineContext: Record<string, unknown> } = await req.json()

  const machineSummary = `- Machine: ${machineContext.name} (${machineContext.type})
- Status: ${machineContext.status}
- Health Score: ${machineContext.health}%
- Failure Probability: ${machineContext.failureProbability}%
- Estimated Time to Failure: ${machineContext.timeToFailure}
- Temperature: ${machineContext.temperature}°C
- Vibration: ${machineContext.vibration} mm/s
- RPM: ${machineContext.rpm}
- Pressure: ${machineContext.pressure} bar`

  // Without a Gemini key here, answer through the backend copilot (which has its own key and fallbacks)
  if (!googleApiKey) {
    return backendCopilotResponse(messages, machineSummary)
  }

  const systemPrompt = `You are SENTINEL AI, an advanced industrial predictive maintenance AI copilot for PLANT-7 NORTH manufacturing facility. You analyze real-time sensor data and provide actionable maintenance insights.

Current machine context:
${machineSummary}

You are an expert in industrial machinery diagnostics, predictive maintenance, vibration analysis, thermal imaging, and failure mode analysis. Provide concise, technical, and actionable insights. Use industrial terminology. Keep responses under 150 words. Format key data points clearly.`

  const google = createGoogleGenerativeAI({ apiKey: googleApiKey })
  const result = streamText({
    model: google('gemini-2.5-flash'),
    system: systemPrompt,
    messages: await convertToModelMessages(messages),
    abortSignal: req.signal,
  })

  return result.toUIMessageStreamResponse({
    onError: () => 'The AI copilot could not answer right now (Gemini request failed). Please try again shortly.',
  })
}

function backendCopilotResponse(messages: UIMessage[], machineSummary: string) {
  const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
  const question = lastUserMessage?.parts
    .map(p => (p.type === 'text' ? p.text : ''))
    .join('') ?? ''

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      let answer: string
      try {
        const res = await fetch(ENDPOINTS.copilotChat, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: question,
            user_id: 'dashboard',
            context: { machine: machineSummary },
          }),
        })
        if (!res.ok) throw new Error(`Copilot API error: ${res.status}`)
        answer = (await res.json()).response || 'No response from the copilot.'
      } catch {
        answer = 'The SENTINEL backend is unreachable right now (it may be waking up). Please try again in a moment.'
      }

      const id = crypto.randomUUID()
      writer.write({ type: 'text-start', id })
      writer.write({ type: 'text-delta', id, delta: answer })
      writer.write({ type: 'text-end', id })
    },
  })

  return createUIMessageStreamResponse({ stream })
}

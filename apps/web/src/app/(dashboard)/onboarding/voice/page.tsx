"use client"

import { useState, useRef, useCallback } from "react"
import { useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { useRouter } from "next/navigation"
import {
  Mic, MicOff, Upload, Loader2, CheckCircle, ChevronRight,
  Volume2, AudioLines, FileAudio, AlertCircle, ArrowRight
} from "lucide-react"

interface ExtractedProject {
  name: string | null
  description: string | null
  project_type: string | null
  location: string | null
  capacity_mw: number | null
  total_investment_needed: number | null
  currency: string | null
  stage: string | null
  technology: string | null
  irr_target: number | null
  timeline_months: number | null
}

type RecordingState = "idle" | "recording" | "processing" | "done" | "error"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionType = any

declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionType
    webkitSpeechRecognition: SpeechRecognitionType
  }
}

export default function VoiceInputPage() {
  const router = useRouter()
  const [recordingState, setRecordingState] = useState<RecordingState>("idle")
  const [transcript, setTranscript] = useState("")
  const [extracted, setExtracted] = useState<ExtractedProject | null>(null)
  const [editedFields, setEditedFields] = useState<Partial<ExtractedProject>>({})
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioSeconds, setAudioSeconds] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recognitionRef = useRef<SpeechRecognitionType | null>(null)

  const processMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append("audio", file)
      return api.post("/voice/process", form, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data)
    },
    onSuccess: (data) => {
      setTranscript(data.transcript ?? "")
      setExtracted(data.extracted_data ?? null)
      setRecordingState("done")
    },
    onError: () => setRecordingState("error"),
  })

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []
      setAudioSeconds(0)
      setRecordingState("recording")

      // Browser speech recognition for live transcript
      const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition
      if (SR) {
        const recognition = new SR()
        recognition.continuous = true
        recognition.interimResults = true
        recognition.onresult = (e: SpeechRecognitionType) => {
          let interim = ""
          for (let i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) setTranscript(t => t + e.results[i][0].transcript + " ")
            else interim += e.results[i][0].transcript
          }
        }
        recognition.start()
        recognitionRef.current = recognition
      }

      const recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        setAudioBlob(blob)
        stream.getTracks().forEach(t => t.stop())
      }
      recorder.start(100)
      mediaRecorderRef.current = recorder

      timerRef.current = setInterval(() => setAudioSeconds(s => s + 1), 1000)
    } catch {
      setRecordingState("error")
    }
  }, [])

  const stopRecording = useCallback(() => {
    recognitionRef.current?.stop()
    mediaRecorderRef.current?.stop()
    if (timerRef.current) clearInterval(timerRef.current)
    setRecordingState("processing")
  }, [])

  const processAudio = useCallback(() => {
    if (!audioBlob) return
    const file = new File([audioBlob], "recording.webm", { type: audioBlob.type })
    processMutation.mutate(file)
  }, [audioBlob, processMutation])

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setRecordingState("processing")
    processMutation.mutate(file)
  }, [processMutation])

  // After recording stops → auto process
  const handleStop = useCallback(() => {
    stopRecording()
    // processAudio called after state update + blob set via useEffect alternative
    setTimeout(() => {
      if (chunksRef.current.length > 0) {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        const file = new File([blob], "recording.webm", { type: blob.type })
        processMutation.mutate(file)
      }
    }, 300)
  }, [stopRecording, processMutation])

  const fieldValue = (key: keyof ExtractedProject) =>
    editedFields[key] !== undefined ? editedFields[key] : extracted?.[key]

  const setField = (key: keyof ExtractedProject, value: string | number | null) =>
    setEditedFields(prev => ({ ...prev, [key]: value }))

  const proceedToOnboarding = () => {
    const params = new URLSearchParams()
    const merged = { ...extracted, ...editedFields }
    Object.entries(merged).forEach(([k, v]) => { if (v != null) params.set(k, String(v)) })
    router.push(`/onboarding?${params.toString()}`)
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Voice Project Input</h1>
        <p className="text-sm text-gray-500 mt-1">Describe your project naturally — we'll extract the details automatically</p>
      </div>

      {/* Recording panel */}
      <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center space-y-6">
        {recordingState === "idle" && (
          <>
            <div className="flex justify-center">
              <div className="h-24 w-24 rounded-full bg-primary-50 flex items-center justify-center">
                <Mic className="h-10 w-10 text-primary-600" />
              </div>
            </div>
            <div>
              <p className="font-semibold text-gray-900">Ready to record</p>
              <p className="text-sm text-gray-500 mt-1">Speak naturally about your project — location, capacity, technology, investment needed</p>
            </div>
            <div className="flex justify-center gap-4">
              <button
                onClick={startRecording}
                className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 font-medium"
              >
                <Mic className="h-5 w-5" />
                Start Recording
              </button>
              <label className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-xl hover:bg-gray-50 cursor-pointer font-medium text-gray-700">
                <Upload className="h-5 w-5" />
                Upload Audio
                <input type="file" className="hidden" accept="audio/*" onChange={handleFileUpload} />
              </label>
            </div>
            <p className="text-xs text-gray-400">Supports MP3, WAV, M4A, OGG, WebM · Max 25MB</p>
          </>
        )}

        {recordingState === "recording" && (
          <>
            <div className="flex justify-center">
              <div className="relative h-24 w-24">
                <div className="absolute inset-0 rounded-full bg-red-100 animate-ping opacity-40" />
                <div className="relative h-24 w-24 rounded-full bg-red-500 flex items-center justify-center">
                  <Mic className="h-10 w-10 text-white" />
                </div>
              </div>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-lg">Recording…</p>
              <p className="text-sm text-gray-500 mt-1">
                {Math.floor(audioSeconds / 60)}:{String(audioSeconds % 60).padStart(2, "0")}
              </p>
            </div>
            {transcript && (
              <div className="text-left bg-gray-50 rounded-xl p-4 text-sm text-gray-700 max-h-32 overflow-y-auto">
                {transcript}
              </div>
            )}
            <button
              onClick={handleStop}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 font-medium mx-auto"
            >
              <MicOff className="h-5 w-5" />
              Stop Recording
            </button>
          </>
        )}

        {recordingState === "processing" && (
          <>
            <div className="flex justify-center">
              <div className="h-24 w-24 rounded-full bg-blue-50 flex items-center justify-center">
                <Loader2 className="h-10 w-10 text-blue-600 animate-spin" />
              </div>
            </div>
            <p className="font-semibold text-gray-900">Processing audio…</p>
            <p className="text-sm text-gray-500">Transcribing and extracting project details</p>
          </>
        )}

        {recordingState === "error" && (
          <>
            <div className="flex justify-center">
              <div className="h-24 w-24 rounded-full bg-red-50 flex items-center justify-center">
                <AlertCircle className="h-10 w-10 text-red-400" />
              </div>
            </div>
            <p className="font-semibold text-gray-900">Processing failed</p>
            <p className="text-sm text-gray-500">Please try again or upload a different audio file</p>
            <button
              onClick={() => setRecordingState("idle")}
              className="px-6 py-3 border border-gray-300 rounded-xl hover:bg-gray-50 font-medium text-gray-700 mx-auto"
            >
              Try Again
            </button>
          </>
        )}
      </div>

      {/* Extracted fields — only shown when done */}
      {recordingState === "done" && extracted && (
        <div className="space-y-6">
          {/* Transcript */}
          {transcript && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-3">
                <FileAudio className="h-4 w-4 text-gray-400" />
                <h2 className="font-semibold text-gray-900 text-sm">Transcript</h2>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">{transcript}</p>
            </div>
          )}

          {/* Extracted fields */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <h2 className="font-semibold text-gray-900 text-sm">Extracted Project Data</h2>
              <span className="text-xs text-gray-500">— review and edit before continuing</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {([
                ["name", "Project Name", "text"],
                ["project_type", "Project Type", "text"],
                ["location", "Location", "text"],
                ["technology", "Technology", "text"],
                ["stage", "Stage", "text"],
                ["capacity_mw", "Capacity (MW)", "number"],
                ["total_investment_needed", "Investment Needed ($)", "number"],
                ["irr_target", "IRR Target (%)", "number"],
                ["timeline_months", "Timeline (months)", "number"],
              ] as [keyof ExtractedProject, string, string][]).map(([key, label, type]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input
                    type={type}
                    className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                    value={String(fieldValue(key) ?? "")}
                    onChange={e => setField(key, type === "number" ? (e.target.value ? Number(e.target.value) : null) : e.target.value || null)}
                    placeholder="Not detected"
                  />
                </div>
              ))}
            </div>

            {extracted.description && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <textarea
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm resize-none"
                  value={String(fieldValue("description") ?? "")}
                  onChange={e => setField("description", e.target.value || null)}
                />
              </div>
            )}

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={() => setRecordingState("idle")}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Start over
              </button>
              <button
                onClick={proceedToOnboarding}
                className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700 font-medium"
              >
                Continue to Onboarding
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

interface UseVoiceRecognitionOptions {
  wakeWord?: string;
  wakeWordEnabled?: boolean;
  language?: string;
  onCommandDetected?: (text: string) => void;
  onError?: (err: string) => void;
}

export function useVoiceRecognition({
  wakeWord = 'hey assistant',
  wakeWordEnabled = true,
  language = 'en',
  onCommandDetected,
  onError,
}: UseVoiceRecognitionOptions) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);

  const finalTranscriptRef = useRef<string>('');
  const recognitionRef = useRef<any>(null);
  const wakeWordRecognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Audio level visualizer simulation / mic stream
  const setupAudioAnalyzer = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
        }
        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch (e) {
      // Simulate level if mic stream restricted
      setAudioLevel(50);
    }
  };

  const stopAudioAnalyzer = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
    }
    setAudioLevel(0);
  };

  // Push-to-Talk via Web Speech API or MediaRecorder
  const startListening = useCallback(async () => {
    finalTranscriptRef.current = '';
    setTranscript('');
    setIsListening(true);
    setupAudioAnalyzer();

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

        recognition.onresult = (event: any) => {
          let current = '';
          for (let i = 0; i < event.results.length; i++) {
            current += event.results[i][0].transcript;
          }
          finalTranscriptRef.current = current;
          setTranscript(current);
        };

        recognition.onend = () => {
          setIsListening(false);
          stopAudioAnalyzer();
          const spokenText = finalTranscriptRef.current.trim();
          if (spokenText) {
            if (onCommandDetected) onCommandDetected(spokenText);
          }
        };

        recognition.onerror = (event: any) => {
          setIsListening(false);
          stopAudioAnalyzer();
          if (event.error !== 'no-speech' && onError) {
            onError(`Speech error: ${event.error}`);
          }
        };

        recognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (e) {
        console.warn('Web Speech API start error, falling back to MediaRecorder:', e);
      }
    }

    // MediaRecorder fallback
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setIsListening(false);
        setIsProcessing(true);
        stopAudioAnalyzer();

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        try {
          const res = await api.transcribeAudioBlob(audioBlob);
          setIsProcessing(false);
          if (res.success && res.text) {
            finalTranscriptRef.current = res.text;
            setTranscript(res.text);
            if (onCommandDetected) onCommandDetected(res.text);
          } else {
            if (onError) onError(res.error || "Could not understand audio.");
          }
        } catch (err: any) {
          setIsProcessing(false);
          if (onError) onError(err.message || "Audio transcription failed.");
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
    } catch (err: any) {
      setIsListening(false);
      stopAudioAnalyzer();
      if (onError) onError("Microphone access denied or unavailable.");
    }
  }, [language, onCommandDetected, onError]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
    stopAudioAnalyzer();
  }, []);

  // Continuous Wake-Word Detection Listener in background
  useEffect(() => {
    if (!wakeWordEnabled || isListening) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      const wakeRecognizer = new SpeechRecognition();
      wakeRecognizer.continuous = true;
      wakeRecognizer.interimResults = true;
      wakeRecognizer.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      wakeRecognizer.onresult = (event: any) => {
        const lastResultIndex = event.results.length - 1;
        const heard = event.results[lastResultIndex][0].transcript.toLowerCase().trim();
        const wakeTarget = (wakeWord || 'hey assistant').toLowerCase();

        if (heard.includes(wakeTarget) || heard.includes('hey assistant') || heard.includes('hey aura') || heard.includes('assistant')) {
          try {
            wakeRecognizer.stop();
          } catch (e) {}
          // Start active listening!
          startListening();
        }
      };

      wakeRecognizer.onerror = () => {
        // Silently restart on error
      };

      wakeRecognizer.onend = () => {
        // Keep listening in background if still enabled and not active
        if (wakeWordEnabled && !isListening) {
          try {
            wakeRecognizer.start();
          } catch (e) {}
        }
      };

      wakeWordRecognitionRef.current = wakeRecognizer;
      wakeRecognizer.start();

      return () => {
        try {
          wakeRecognizer.stop();
        } catch (e) {}
      };
    } catch (e) {}
  }, [wakeWordEnabled, isListening, language, wakeWord, startListening]);

  return {
    isListening,
    isProcessing,
    transcript,
    audioLevel,
    startListening,
    stopListening,
  };
}

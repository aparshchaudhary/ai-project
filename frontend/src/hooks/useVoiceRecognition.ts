import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

export type ListeningMode = 'push_to_talk' | 'continuous';

interface UseVoiceRecognitionOptions {
  wakeWord?: string;
  wakeWordEnabled?: boolean;
  language?: string;
  mode?: ListeningMode;
  onCommandDetected?: (text: string) => void;
  onError?: (err: string) => void;
}

export function useVoiceRecognition({
  wakeWord = 'hey assistant',
  wakeWordEnabled = true,
  language = 'en',
  mode = 'push_to_talk',
  onCommandDetected,
  onError,
}: UseVoiceRecognitionOptions) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [lastRecognizedCommand, setLastRecognizedCommand] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);
  const [listeningDuration, setListeningDuration] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'listening' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const finalTranscriptRef = useRef<string>('');
  const recognitionRef = useRef<any>(null);
  const wakeWordRecognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const durationIntervalRef = useRef<any>(null);
  const isExplicitlyStoppedRef = useRef<boolean>(false);
  const lastProcessedTextRef = useRef<string>('');
  const lastProcessedTimeRef = useRef<number>(0);
  const modeRef = useRef<ListeningMode>(mode);

  // Keep modeRef synchronized with current mode
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // Audio stream & level visualizer using persistent MediaStream
  const setupAudioAnalyzer = async () => {
    try {
      // Reuse existing active media stream if tracks are live
      let stream = mediaStreamRef.current;
      if (!stream || stream.getTracks().every(t => t.readyState === 'ended')) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
      }

      setConnectionStatus('listening');

      // Initialize Web Audio Context if not exists or closed
      if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioCtx;
      } else if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      const audioCtx = audioContextRef.current;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyser.smoothingTimeConstant = 0.6;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
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
    } catch (e: any) {
      console.warn('Microphone stream access error:', e);
      setAudioLevel(35); // fallback simulated level
      setErrorMessage(e.message || 'Microphone access restricted.');
    }
  };

  const stopAudioAnalyzer = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => {
        try {
          track.stop();
        } catch (e) {}
      });
      mediaStreamRef.current = null;
    }
    setAudioLevel(0);
  };

  // Start duration counter
  const startTimer = () => {
    if (durationIntervalRef.current) clearInterval(durationIntervalRef.current);
    setListeningDuration(0);
    const start = Date.now();
    durationIntervalRef.current = setInterval(() => {
      setListeningDuration(Math.floor((Date.now() - start) / 1000));
    }, 1000);
  };

  const stopTimer = () => {
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }
    setListeningDuration(0);
  };

  // Command delivery with 1.8s duplicate protection
  const dispatchCommand = useCallback((rawText: string) => {
    const text = rawText.trim();
    if (!text) return;

    const now = Date.now();
    if (lastProcessedTextRef.current.toLowerCase() === text.toLowerCase() && (now - lastProcessedTimeRef.current < 1800)) {
      return; // Ignore duplicate
    }
    lastProcessedTextRef.current = text;
    lastProcessedTimeRef.current = now;
    setLastRecognizedCommand(text);

    if (onCommandDetected) {
      onCommandDetected(text);
    }
  }, [onCommandDetected]);

  // Main start listening handler
  const startListening = useCallback(async () => {
    isExplicitlyStoppedRef.current = false;
    finalTranscriptRef.current = '';
    setTranscript('');
    setErrorMessage(null);
    setIsListening(true);
    setConnectionStatus('connecting');

    startTimer();
    await setupAudioAnalyzer();

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        // In continuous mode, keep recognizing phrases continuously
        recognition.continuous = modeRef.current === 'continuous';
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';

        recognition.onstart = () => {
          setIsListening(true);
          setConnectionStatus('listening');
        };

        recognition.onresult = (event: any) => {
          let interimText = '';
          let finalText = '';

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const piece = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalText += piece;
            } else {
              interimText += piece;
            }
          }

          const currentDisplay = (finalText || interimText).trim();
          if (currentDisplay) {
            finalTranscriptRef.current = currentDisplay;
            setTranscript(currentDisplay);
          }

          if (finalText.trim()) {
            dispatchCommand(finalText.trim());
            // If Push-to-Talk mode, stop after successful command
            if (modeRef.current === 'push_to_talk') {
              stopListening();
            } else {
              // In continuous mode, reset the local transcript buffer for the next utterance
              finalTranscriptRef.current = '';
              setTranscript('');
            }
          }
        };

        recognition.onend = () => {
          // If continuous listening is enabled and user hasn't explicitly clicked stop, restart smoothly
          if (modeRef.current === 'continuous' && !isExplicitlyStoppedRef.current) {
            try {
              recognition.start();
              return;
            } catch (restartErr) {
              // If rapid restart is throttled, retry in 300ms
              setTimeout(() => {
                if (modeRef.current === 'continuous' && !isExplicitlyStoppedRef.current) {
                  try { recognition.start(); } catch (e) {}
                }
              }, 300);
              return;
            }
          }

          setIsListening(false);
          setConnectionStatus('idle');
          stopAudioAnalyzer();
          stopTimer();

          // Push-to-talk final fallback if onresult didn't emit final flag
          const leftover = finalTranscriptRef.current.trim();
          if (leftover && modeRef.current === 'push_to_talk') {
            dispatchCommand(leftover);
          }
        };

        recognition.onerror = (event: any) => {
          if (event.error === 'no-speech') {
            // In continuous mode, no-speech is normal silence; let onend smoothly loop
            if (modeRef.current === 'continuous') return;
          }
          if (event.error === 'aborted') {
            return;
          }

          console.warn('SpeechRecognition error:', event.error);
          if (event.error === 'not-allowed') {
            const msg = 'Microphone permission denied. Please allow microphone access.';
            setErrorMessage(msg);
            if (onError) onError(msg);
          } else if (event.error !== 'no-speech' && onError) {
            onError(`Microphone notice: ${event.error}`);
          }
        };

        recognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (e: any) {
        console.warn('SpeechRecognition start failed, falling back to MediaRecorder:', e);
      }
    }

    // Fallback: MediaRecorder backend chunk streaming
    try {
      let stream = mediaStreamRef.current;
      if (!stream || stream.getTracks().every(t => t.readyState === 'ended')) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
      }

      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stopAudioAnalyzer();
        stopTimer();

        if (isExplicitlyStoppedRef.current && audioChunksRef.current.length === 0) {
          setIsListening(false);
          setConnectionStatus('idle');
          return;
        }

        setIsListening(false);
        setIsProcessing(true);
        setConnectionStatus('connected');

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        try {
          const res = await api.transcribeAudioBlob(audioBlob);
          setIsProcessing(false);
          setConnectionStatus('idle');
          if (res.success && res.text) {
            finalTranscriptRef.current = res.text;
            setTranscript(res.text);
            dispatchCommand(res.text);
          } else if (onError) {
            onError(res.error || 'Could not understand audio.');
          }
        } catch (err: any) {
          setIsProcessing(false);
          setConnectionStatus('idle');
          if (onError) onError(err.message || 'Audio transcription failed.');
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(500); // 500ms chunks
    } catch (err: any) {
      setIsListening(false);
      setConnectionStatus('error');
      stopAudioAnalyzer();
      stopTimer();
      const msg = 'Microphone access denied or unavailable.';
      setErrorMessage(msg);
      if (onError) onError(msg);
    }
  }, [language, dispatchCommand, onError]);

  // Explicit stop listening handler
  const stopListening = useCallback(() => {
    isExplicitlyStoppedRef.current = true;
    setIsListening(false);
    setConnectionStatus('idle');
    stopTimer();

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

    stopAudioAnalyzer();
  }, []);

  // Continuous Wake-Word Detection Listener in background (only when NOT actively listening)
  useEffect(() => {
    if (!wakeWordEnabled || isListening) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    let wakeRecognizer: any = null;
    let isCancelled = false;

    try {
      wakeRecognizer = new SpeechRecognition();
      wakeRecognizer.continuous = true;
      wakeRecognizer.interimResults = true;
      wakeRecognizer.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      wakeRecognizer.onresult = (event: any) => {
        if (isCancelled) return;
        const lastResultIndex = event.results.length - 1;
        const heard = event.results[lastResultIndex][0].transcript.toLowerCase().trim();
        const wakeTarget = (wakeWord || 'hey assistant').toLowerCase();

        if (heard.includes(wakeTarget) || heard.includes('hey assistant') || heard.includes('hey aura') || heard.includes('assistant')) {
          try {
            wakeRecognizer.stop();
          } catch (e) {}
          startListening();
        }
      };

      wakeRecognizer.onerror = () => {};

      wakeRecognizer.onend = () => {
        if (wakeWordEnabled && !isListening && !isCancelled) {
          try {
            wakeRecognizer.start();
          } catch (e) {}
        }
      };

      wakeWordRecognitionRef.current = wakeRecognizer;
      wakeRecognizer.start();
    } catch (e) {}

    return () => {
      isCancelled = true;
      if (wakeRecognizer) {
        try {
          wakeRecognizer.stop();
        } catch (e) {}
      }
    };
  }, [wakeWordEnabled, isListening, language, wakeWord, startListening]);

  return {
    isListening,
    isProcessing,
    transcript,
    lastRecognizedCommand,
    audioLevel,
    listeningDuration,
    connectionStatus,
    errorMessage,
    startListening,
    stopListening,
  };
}

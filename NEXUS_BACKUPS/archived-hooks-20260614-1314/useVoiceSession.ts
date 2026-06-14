import { useState, useCallback } from 'react';

export function useVoiceSession() {
  const [isListening, setIsListening] = useState(false);
  const [volume, setVolume] = useState(0);

  const startListening = useCallback(() => {
    setIsListening(true);
    // TODO: Connect to Stream Video + Vision Agents backend
  }, []);

  const stopListening = useCallback(() => {
    setIsListening(false);
    setVolume(0);
    // TODO: Disconnect from backend
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    volume,
    startListening,
    stopListening,
    toggleListening,
  };
}

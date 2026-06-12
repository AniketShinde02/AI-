class PlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Use a Float32Array as a ring buffer or similar would be overkill for 16kHz
    // but we can definitely use a TypedArray with a manual head/tail for performance.
    this.bufferSize = 48000; // 3 seconds of audio at 16kHz
    this.buffer = new Float32Array(this.bufferSize);
    this.head = 0;
    this.tail = 0;
    this.count = 0;
    this.isPlaying = false;
    this.isStreamFinished = false;
    this.starvationFrames = 0;
    
    // Instrumentation
    this.starvationEvents = 0;
    this.playbackInterruptions = 0;
    this.metricsInterval = 100; // Log roughly every 100 process() calls
    this.processCount = 0;

    this.port.onmessage = (e) => {
      if (e.data && e.data.type === 'clear') {
        this.head = 0;
        this.tail = 0;
        this.count = 0;
        this.isPlaying = false;
        this.isStreamFinished = false;
        this.starvationFrames = 0;
        return;
      }

      if (e.data && e.data.type === 'stream_end') {
        this.isStreamFinished = true;
        return;
      }
      
      // Expects Float32Array
      const incoming = e.data;
      for (let i = 0; i < incoming.length; i++) {
        if (this.count < this.bufferSize) {
          this.buffer[this.tail] = incoming[i];
          this.tail = (this.tail + 1) % this.bufferSize;
          this.count++;
        }
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs[0];
    const channelCount = output.length;
    const samplesNeeded = output[0].length;

    // Jitter Buffer: Reduced from 12800 (800ms) to 3200 (200ms) to eliminate dead silence gap
    const minBuffer = 3200;

    if (this.count >= samplesNeeded && (this.isPlaying || this.count >= minBuffer || this.isStreamFinished)) {
      if (!this.isPlaying) {
        this.isPlaying = true;
        this.starvationFrames = 0;
      }
      
      // Fill all output channels with the same data (Mono -> Stereo/N-channel)
      for (let i = 0; i < samplesNeeded; i++) {
        const sample = this.buffer[this.head];
        this.head = (this.head + 1) % this.bufferSize;
        this.count--;
        
        for (let channel = 0; channel < channelCount; channel++) {
          output[channel][i] = sample;
        }
      }
    } else {
      // Buffer empty or under-filled
      if (this.isPlaying) {
        // Only end playback if we received the 'stream_end' flag and the buffer is drained.
        if (this.isStreamFinished && this.count === 0) {
          this.isPlaying = false;
          this.isStreamFinished = false;
          this.port.postMessage({ type: 'playback_finished' });
        } else if (!this.isStreamFinished) {
          this.starvationEvents++;
          if (this.starvationEvents === 1) { // Only count the first starvation event per burst
              this.playbackInterruptions++;
          }
        }
      }
      
      // Zero-fill all channels
      for (let channel = 0; channel < channelCount; channel++) {
        output[channel].fill(0);
      }
    }
    
    // Instrumentation logging
    this.processCount++;
    if (this.processCount % this.metricsInterval === 0) {
      const fillPercent = ((this.count / this.bufferSize) * 100).toFixed(2);
      this.port.postMessage({
        type: 'metrics',
        data: {
            current_buffer_size: this.count,
            fill_percent: fillPercent,
            empty_percent: (100 - fillPercent).toFixed(2),
            starvation_events: this.starvationEvents,
            playback_interruptions: this.playbackInterruptions
        }
      });
      // Reset starvation events after logging to get per-interval counts
      this.starvationEvents = 0;
    }
    
    return true;
  }
}

registerProcessor('playback-processor', PlaybackProcessor);

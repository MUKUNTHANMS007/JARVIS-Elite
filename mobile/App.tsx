import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, Text, View, TouchableOpacity, 
  Dimensions, Animated, StatusBar, ScrollView 
} from 'react-native';
import { Audio } from 'expo-av';
import * as Notifications from 'expo-notifications';
import { 
  Mic, MicOff, Zap, Code, 
  BookOpen, Activity, Settings, 
  MessageSquare, Music 
} from 'lucide-react-native';

const { width } = Dimensions.get('window');

// --- CONFIG ---
const BACKEND_URL = "ws://192.168.1.5:8000/ws/voice"; // Replace with your laptop IP
const VAD_THRESHOLD = -45; // dB
const SILENCE_DURATION = 800; // ms

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [lastTranscript, setLastTranscript] = useState("Standing by...");
  
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const socketRef = useRef<WebSocket | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // --- Neural Pulse Animation ---
  useEffect(() => {
    if (isRecording || isThinking) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 800, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isRecording, isThinking]);

  // --- WebSocket Setup ---
  useEffect(() => {
    connectWS();
    return () => socketRef.current?.close();
  }, []);

  const connectWS = () => {
    const ws = new WebSocket(BACKEND_URL);
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(connectWS, 3000);
    };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'TRANSCRIPTION') setLastTranscript(data.text);
      if (data.type === 'TURN_START') setIsThinking(true);
      if (data.type === 'TURN_COMPLETE') setIsThinking(false);
    };
    socketRef.current = ws;
  };

  // --- Voice Pipeline with VAD ---
  const startRecording = async () => {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      recordingRef.current = recording;
      setIsRecording(true);

      // Simple VAD Logic
      recording.setOnRecordingStatusUpdate((status) => {
        if (status.metering !== undefined) {
          if (status.metering > VAD_THRESHOLD) {
            // Speech detected - reset silence timer
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = null;
            }
          } else {
            // Silence detected - start timer if not already running
            if (!silenceTimerRef.current) {
              silenceTimerRef.current = setTimeout(stopRecording, SILENCE_DURATION);
            }
          }
        }
      });

    } catch (err) {
      console.error('Failed to start recording', err);
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    
    setIsRecording(false);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

    await recordingRef.current.stopAndUnloadAsync();
    const uri = recordingRef.current.getURI();
    recordingRef.current = null;

    if (uri && socketRef.current?.readyState === WebSocket.OPEN) {
      // Send audio to backend
      const response = await fetch(uri);
      const blob = await response.blob();
      const reader = new FileReader();
      reader.onload = () => {
        const base64Audio = (reader.result as string).split(',')[1];
        socketRef.current?.send(JSON.stringify({ type: 'AUDIO_START', data: base64Audio }));
      };
      reader.readAsDataURL(blob);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Good Morning,</Text>
          <Text style={styles.userName}>Mukunthan</Text>
        </View>
        <TouchableOpacity style={styles.settingsBtn}>
          <Settings size={20} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Neural Heart Section */}
      <View style={styles.heartSection}>
        <Animated.View style={[styles.pulseCircle, { transform: [{ scale: pulseAnim }] }]}>
          <TouchableOpacity 
            style={[styles.mainOrb, isRecording && styles.activeOrb]} 
            onLongPress={startRecording}
            onPressOut={stopRecording}
          >
            {isRecording ? <Mic size={40} color="#fff" /> : <Zap size={40} color="#00d2ff" />}
          </TouchableOpacity>
        </Animated.View>
        <Text style={styles.statusText}>{isConnected ? "NEURAL LINK ACTIVE" : "SYNCING..."}</Text>
        <Text style={styles.transcriptText}>{lastTranscript}</Text>
      </View>

      {/* Bento Grid */}
      <ScrollView contentContainerStyle={styles.gridContainer} showsVerticalScrollIndicator={false}>
        <View style={styles.gridRow}>
          <View style={[styles.card, { flex: 1.5, backgroundColor: '#121212' }]}>
            <Code size={24} color="#00d2ff" />
            <Text style={styles.cardTitle}>LeetCode</Text>
            <Text style={styles.cardVal}>12 Day Streak</Text>
            <Text style={styles.cardSub}>250 Solved</Text>
          </View>
          <View style={[styles.card, { flex: 1, backgroundColor: '#1a1a1a' }]}>
            <BookOpen size={24} color="#a855f7" />
            <Text style={styles.cardTitle}>Exams</Text>
            <Text style={styles.cardVal}>Day 12</Text>
            <Text style={styles.cardSub}>OS Concepts</Text>
          </View>
        </View>

        <View style={styles.gridRow}>
          <View style={[styles.card, { flex: 1, backgroundColor: '#1a1a1a' }]}>
            <Activity size={24} color="#22c55e" />
            <Text style={styles.cardTitle}>Focus</Text>
            <Text style={styles.cardVal}>4.2h</Text>
            <Text style={styles.cardSub}>Deep Work</Text>
          </View>
          <View style={[styles.card, { flex: 1.5, backgroundColor: '#121212' }]}>
            <Music size={24} color="#ec4899" />
            <Text style={styles.cardTitle}>Spotify</Text>
            <Text style={styles.cardVal}>Now Playing</Text>
            <Text style={styles.cardSub}>Lo-Fi Beats</Text>
          </View>
        </View>

        <TouchableOpacity style={styles.fullCard}>
          <MessageSquare size={20} color="#fff" style={{marginRight: 10}} />
          <Text style={styles.fullCardText}>View Discussion History</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    paddingHorizontal: 20,
    paddingTop: 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 40,
  },
  greeting: {
    color: '#666',
    fontSize: 14,
    fontWeight: '500',
  },
  userName: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  settingsBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  heartSection: {
    alignItems: 'center',
    marginBottom: 40,
  },
  pulseCircle: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(0, 210, 255, 0.05)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  mainOrb: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
    elevation: 10,
    shadowColor: '#00d2ff',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
  },
  activeOrb: {
    backgroundColor: '#00d2ff',
    borderColor: '#fff',
  },
  statusText: {
    color: '#00d2ff',
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    marginTop: 20,
  },
  transcriptText: {
    color: '#999',
    fontSize: 14,
    fontStyle: 'italic',
    marginTop: 10,
    textAlign: 'center',
  },
  gridContainer: {
    paddingBottom: 40,
  },
  gridRow: {
    flexDirection: 'row',
    gap: 15,
    marginBottom: 15,
  },
  card: {
    padding: 20,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#222',
  },
  cardTitle: {
    color: '#666',
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 15,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  cardVal: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 5,
  },
  cardSub: {
    color: '#444',
    fontSize: 12,
    marginTop: 2,
  },
  fullCard: {
    backgroundColor: '#1a1a1a',
    padding: 20,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  fullCardText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
});

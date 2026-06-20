import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, Text, View, TouchableOpacity, 
  Dimensions, Animated, StatusBar, ScrollView,
  Modal, TextInput, Alert
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { 
  Mic, MicOff, Zap, Code, 
  BookOpen, Activity, Settings, 
  MessageSquare, Music 
} from 'lucide-react-native';

const { width } = Dimensions.get('window');
const VAD_THRESHOLD = -45; // dB
const SILENCE_DURATION = 800; // ms

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [lastTranscript, setLastTranscript] = useState("Standing by...");
  const [lastAssistantText, setLastAssistantText] = useState("");
  
  // Configuration & Dynamic Telemetry States
  const [backendHost, setBackendHost] = useState("192.168.1.5:8000");
  const [hostInput, setHostInput] = useState("192.168.1.5:8000");
  const [showSettings, setShowSettings] = useState(false);

  // Live Telemetry States
  const [leetcodeStreak, setLeetcodeStreak] = useState(12);
  const [leetcodeSolved, setLeetcodeSolved] = useState(250);
  const [examDay, setExamDay] = useState("Day 12");
  const [examName, setExamName] = useState("OS Concepts");
  const [focusHours, setFocusHours] = useState(4.2);
  const [spotifyTrack, setSpotifyTrack] = useState("Lo-Fi Beats");
  const [spotifyStatus, setSpotifyStatus] = useState("Now Playing");
  
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const socketRef = useRef<WebSocket | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const assistantTextRef = useRef("");
  const soundRef = useRef<Audio.Sound | null>(null);

  // --- Load backend config ---
  useEffect(() => {
    AsyncStorage.getItem("BACKEND_HOST").then((val) => {
      if (val) {
        setBackendHost(val);
        setHostInput(val);
      }
    });
  }, []);

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

  const blobToBase64 = async (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result.split(',', 2)[1] || '');
        } else {
          reject(new Error('Failed to read audio blob.'));
        }
      };
      reader.onerror = () => reject(reader.error ?? new Error('Failed to read audio blob.'));
      reader.readAsDataURL(blob);
    });
  };

  const speakAssistantText = async (text: string) => {
    if (!text.trim()) return;

    try {
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }

      const response = await fetch(`http://${backendHost}/api/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        console.warn('Assistant speech request failed', response.status);
        return;
      }

      const blob = await response.blob();
      const audioBase64 = await blobToBase64(blob);
      const extension = response.headers.get('content-type')?.includes('mpeg') ? 'mp3' : 'wav';
      const fileUri = `${FileSystem.cacheDirectory ?? FileSystem.documentDirectory}jarvis-tts-${Date.now()}.${extension}`;
      await FileSystem.writeAsStringAsync(fileUri, audioBase64, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const { sound } = await Audio.Sound.createAsync({ uri: fileUri }, { shouldPlay: true });
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status: any) => {
        if (status?.didJustFinish) {
          sound.unloadAsync().catch(() => {});
          FileSystem.deleteAsync(fileUri, { idempotent: true }).catch(() => {});
          if (soundRef.current === sound) {
            soundRef.current = null;
          }
        }
      });
    } catch (error) {
      console.error('Failed to play assistant speech', error);
    }
  };

  // --- WebSocket Setup ---
  useEffect(() => {
    connectWS();
    return () => {
      socketRef.current?.close();
      soundRef.current?.unloadAsync().catch(() => {});
    };
  }, [backendHost]);

  const connectWS = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    const wsUrl = `ws://${backendHost}/ws/voice`;
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => {
      setIsConnected(false);
      if (socketRef.current === ws) {
        setTimeout(connectWS, 3000);
      }
    };
    ws.onmessage = (e) => {
      if (typeof e.data !== 'string') return;

      try {
        const data = JSON.parse(e.data);
        if (data.type === 'TRANSCRIPTION') setLastTranscript(data.text);
        if (data.type === 'TURN_START') {
          setIsThinking(true);
          assistantTextRef.current = "";
          setLastAssistantText("");
        }
        if (data.type === 'TEXT_CHUNK') {
          assistantTextRef.current += data.text || "";
          setLastAssistantText(assistantTextRef.current);
        }
        if (data.type === 'TURN_COMPLETE') {
          setIsThinking(false);
          const finalText = assistantTextRef.current.trim();
          if (finalText) {
            speakAssistantText(finalText);
          }
        }
      } catch (err) {
        console.error("[WS] Message parsing failed:", err);
      }
    };
    socketRef.current = ws;
  };

  // --- Live Sync Telemetry ---
  const fetchSyncData = async () => {
    try {
      const res = await fetch(`http://${backendHost}/api/sync`);
      if (res.ok) {
        const data = await res.json();
        const intel = data.intelligence || {};
        const leetcode = intel.leetcode || {};
        if (leetcode.streak !== undefined) setLeetcodeStreak(leetcode.streak);
        if (leetcode.total_solved !== undefined) setLeetcodeSolved(leetcode.total_solved);
        
        if (data.focus?.deep_work_hours !== undefined) {
          setFocusHours(data.focus.deep_work_hours);
        }
        
        const track = intel.spotify_track;
        if (track) {
          setSpotifyTrack(track);
          if (track === "Inactive" || track === "Standby") {
            setSpotifyStatus("Paused");
          } else if (track === "Premium Required") {
            setSpotifyStatus("Restricted");
          } else {
            setSpotifyStatus("Now Playing");
          }
        }

        const radar = intel.academic_radar || [];
        if (radar.length > 0) {
          setExamDay(`Day ${radar[0].date}`);
          setExamName(radar[0].title);
        }
      }
    } catch (error) {
      console.debug("Failed to sync backend telemetry:", error);
    }
  };

  useEffect(() => {
    fetchSyncData();
    const timer = setInterval(fetchSyncData, 10000);
    return () => clearInterval(timer);
  }, [backendHost]);

  // --- Voice Pipeline with VAD ---
  const startRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert("Permission Required", "Microphone access is required to speak with JARVIS.");
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        {
          ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
          isMeteringEnabled: true,
        }
      );
      
      recordingRef.current = recording;
      setIsRecording(true);

      recording.setOnRecordingStatusUpdate((status) => {
        if (status.metering !== undefined) {
          if (status.metering > VAD_THRESHOLD) {
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current);
              silenceTimerRef.current = null;
            }
          } else {
            if (!silenceTimerRef.current) {
              silenceTimerRef.current = setTimeout(stopRecording, SILENCE_DURATION);
            }
          }
        }
      });

    } catch (err) {
      console.error('Failed to start recording', err);
      Alert.alert("Recording Failed", `Microphone error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    
    setIsRecording(false);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (uri && socketRef.current?.readyState === WebSocket.OPEN) {
        const response = await fetch(uri);
        const blob = await response.blob();
        const reader = new FileReader();
        reader.onload = () => {
          const base64Audio = (reader.result as string).split(',')[1];
          socketRef.current?.send(JSON.stringify({
            type: 'audio_input',
            data: base64Audio,
            mime_type: blob.type || 'audio/mp4',
            file_name: 'mobile-recording.m4a',
          }));
        };
        reader.readAsDataURL(blob);
      }
    } catch (err) {
      console.error("Failed to stop recording", err);
    }
  };

  const handleSaveSettings = async () => {
    try {
      await AsyncStorage.setItem("BACKEND_HOST", hostInput);
      setBackendHost(hostInput);
      setShowSettings(false);
      Alert.alert("Settings Updated", `Core host set to ${hostInput}`);
    } catch (e) {
      Alert.alert("Error", "Failed to save settings to storage.");
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
        <TouchableOpacity style={styles.settingsBtn} onPress={() => setShowSettings(true)}>
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
        <Text style={styles.transcriptText}>{lastAssistantText || lastTranscript}</Text>
      </View>

      {/* Bento Grid */}
      <ScrollView contentContainerStyle={styles.gridContainer} showsVerticalScrollIndicator={false}>
        <View style={styles.gridRow}>
          <View style={[styles.card, { flex: 1.5, backgroundColor: '#121212' }]}>
            <Code size={24} color="#00d2ff" />
            <Text style={styles.cardTitle}>LeetCode</Text>
            <Text style={styles.cardVal}>{leetcodeStreak} Day Streak</Text>
            <Text style={styles.cardSub}>{leetcodeSolved} Solved</Text>
          </View>
          <View style={[styles.card, { flex: 1, backgroundColor: '#1a1a1a' }]}>
            <BookOpen size={24} color="#a855f7" />
            <Text style={styles.cardTitle}>Exams</Text>
            <Text style={styles.cardVal}>{examDay}</Text>
            <Text style={styles.cardSub}>{examName}</Text>
          </View>
        </View>

        <View style={styles.gridRow}>
          <View style={[styles.card, { flex: 1, backgroundColor: '#1a1a1a' }]}>
            <Activity size={24} color="#22c55e" />
            <Text style={styles.cardTitle}>Focus</Text>
            <Text style={styles.cardVal}>{focusHours}h</Text>
            <Text style={styles.cardSub}>Deep Work</Text>
          </View>
          <View style={[styles.card, { flex: 1.5, backgroundColor: '#121212' }]}>
            <Music size={24} color="#ec4899" />
            <Text style={styles.cardTitle}>Spotify</Text>
            <Text style={styles.cardVal}>{spotifyStatus}</Text>
            <Text style={styles.cardSub}>{spotifyTrack}</Text>
          </View>
        </View>

        <TouchableOpacity style={styles.fullCard}>
          <MessageSquare size={20} color="#fff" style={{marginRight: 10}} />
          <Text style={styles.fullCardText}>View Discussion History</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Settings Modal */}
      <Modal
        visible={showSettings}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowSettings(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>JARVIS COGNITIVE HOST</Text>
            <Text style={styles.modalLabel}>Enter core server IP / Host:</Text>
            <TextInput
              style={styles.modalInput}
              value={hostInput}
              onChangeText={setHostInput}
              placeholder="192.168.1.5:8000"
              placeholderTextColor="#666"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity 
                style={[styles.modalBtn, styles.cancelBtn]} 
                onPress={() => {
                  setHostInput(backendHost);
                  setShowSettings(false);
                }}
              >
                <Text style={styles.btnText}>CANCEL</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.modalBtn, styles.saveBtn]} 
                onPress={handleSaveSettings}
              >
                <Text style={[styles.btnText, { color: '#000', fontWeight: 'bold' }]}>SAVE HOST</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContainer: {
    width: width * 0.85,
    backgroundColor: '#111',
    borderRadius: 28,
    padding: 24,
    borderWidth: 1,
    borderColor: '#333',
  },
  modalTitle: {
    color: '#00d2ff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
    letterSpacing: 1.5,
    marginBottom: 20,
  },
  modalLabel: {
    color: '#aaa',
    fontSize: 12,
    marginBottom: 8,
  },
  modalInput: {
    backgroundColor: '#222',
    color: '#fff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#444',
    marginBottom: 24,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  modalBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  cancelBtn: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
  },
  saveBtn: {
    backgroundColor: '#00d2ff',
  },
  btnText: {
    fontSize: 12,
    letterSpacing: 1,
    color: '#fff',
  },
});

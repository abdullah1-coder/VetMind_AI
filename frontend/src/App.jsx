// frontend/src/App.jsx

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Send, Paperclip, FileText, Download, Plus, 
  User, MessageSquare, Users, Search, RefreshCw, Cat, Sparkles, FolderOpen,
  Edit, Trash2, Calendar, CheckCircle2, XCircle, Clock, LogOut, ChevronDown, Eye, X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = 'https://vetmindai-production.up.railway.app';

// Species and Breed mapping options
const SPECIES_BREEDS = {
  'Feline(cat)': [
    'Domestic Shorthair',
    'Domestic Longhair',
    'Persian',
    'Siamese',
    'Maine Coon',
    'Ragdoll',
    'British Shorthair',
    'Other / Mixed Feline'
  ],
  'Canine(Dog)': [
    'Labrador Retriever',
    'German Shepherd',
    'Golden Retriever',
    'French Bulldog',
    'Beagle',
    'Poodle',
    'Rottweiler',
    'Other / Mixed Canine'
  ],
  'Avian(Bird)': ['Parrot', 'Cockatiel', 'Budgerigar', 'Canary', 'Lovebird', 'Other Avian'],
  'Equine(Horse)': ['Arabian', 'Thoroughbred', 'Quarter Horse', 'Appaloosa', 'Other Equine'],
  'Exotic(Exotic Pet)': ['Rabbit', 'Guinea Pig', 'Hamster', 'Ferret', 'Reptile', 'Other Exotic']
};

export default function App() {
  // -----------------------------------------------------------------
  // AUTH & ROLE STATE
  // -----------------------------------------------------------------
  const [currentUser, setCurrentUser] = useState(null); // { id, email, role, full_name }
  const [isSigningUp, setIsSigningUp] = useState(false);
  const [fullName, setFullName] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState('owner'); // 'doctor' | 'owner'

  // Tab State
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'patients' | 'bookings'
  
  // App State
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientSessions, setPatientSessions] = useState({});
  const [sessionIds, setSessionIds] = useState({});
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Directory Modal Controls
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [viewingPatientRecords, setViewingPatientRecords] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // New Patient Form
  const [newPatient, setNewPatient] = useState({ 
    name: '', 
    species: 'Feline(cat)', 
    breed: 'Domestic Shorthair', 
    age: '', 
    owner_name: '' 
  });

  // Booking State
  const [appointments, setAppointments] = useState([]);
  const [newBooking, setNewBooking] = useState({
    owner_name: '',
    pet_name: '',
    species: 'Canine',
    reason: '',
    appointment_date: '',
    appointment_time: '10:00 AM'
  });

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Set up request interceptor for user data isolation via X-User-ID header
  useEffect(() => {
    const interceptor = axios.interceptors.request.use((config) => {
      if (currentUser?.id) {
        config.headers['X-User-ID'] = currentUser.id;
      }
      return config;
    });

    return () => axios.interceptors.request.eject(interceptor);
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      if (currentUser.role === 'doctor') {
        fetchPatients();
      }
      fetchAppointments();
    }
  }, [currentUser]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchPatients = async () => {
    try {
      const res = await axios.get(`${API_BASE}/patients`);
      setPatients(res.data);
    } catch (err) {
      console.error('Failed to fetch patients:', err);
    }
  };

  const fetchAppointments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/appointments`);
      setAppointments(res.data);
    } catch (err) {
      console.error('Failed to fetch appointments:', err);
    }
  };

  // Switch patient context for doctors
  const handlePatientSelect = (patient) => {
    setSelectedPatient(patient);
    const contextKey = patient ? patient.id : 'general';
    setMessages(patientSessions[contextKey] || []);
  };

  // -----------------------------------------------------------------
  // PATIENT CRUD HANDLERS
  // -----------------------------------------------------------------
  const handleCreatePatient = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_BASE}/patients`, newPatient);
      setPatients([res.data, ...patients]);
      handlePatientSelect(res.data);
      setShowAddModal(false);
      setNewPatient({ name: '', species: 'Feline', breed: 'Domestic Shorthair', age: '', owner_name: '' });
    } catch (err) {
      alert('Error creating patient: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdatePatient = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.put(`${API_BASE}/patients/${editingPatient.id}`, editingPatient);
      setPatients(patients.map(p => p.id === editingPatient.id ? res.data : p));
      if (selectedPatient?.id === editingPatient.id) setSelectedPatient(res.data);
      setEditingPatient(null);
    } catch (err) {
      alert('Error updating patient record: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeletePatient = async (patientId, patientName) => {
    if (!window.confirm(`Are you sure you want to delete patient ${patientName} (#${patientId})?`)) return;
    try {
      await axios.delete(`${API_BASE}/patients/${patientId}`);
      setPatients(patients.filter(p => p.id !== patientId));
      if (selectedPatient?.id === patientId) handlePatientSelect(null);
    } catch (err) {
      alert('Error deleting patient: ' + (err.response?.data?.detail || err.message));
    }
  };

  // -----------------------------------------------------------------
  // AUTH HANDLERS (Supports Sign In & Create Account)
  // -----------------------------------------------------------------
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = isSigningUp ? '/auth/register' : '/auth/login';
      const payload = isSigningUp 
        ? { full_name: fullName, email: loginEmail, password: loginPassword, role: selectedRole }
        : { email: loginEmail, password: loginPassword, role: selectedRole };

      const res = await axios.post(`${API_BASE}${endpoint}`, payload);
      setCurrentUser(res.data.user);
      setActiveTab('chat');
    } catch (err) {
      alert((isSigningUp ? 'Registration' : 'Login') + ' failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setSelectedPatient(null);
    setMessages([]);
    setLoginPassword('');
  };

  // -----------------------------------------------------------------
  // BOOKING HANDLERS
  // -----------------------------------------------------------------
  const handleCreateBooking = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/appointments`, newBooking);
      alert('Appointment request submitted successfully!');
      setNewBooking({
        owner_name: currentUser?.full_name || '',
        pet_name: '',
        species: 'Canine',
        reason: '',
        appointment_date: '',
        appointment_time: '10:00 AM'
      });
      fetchAppointments();
    } catch (err) {
      alert('Booking error: ' + err.message);
    }
  };

  const handleUpdateAptStatus = async (id, status) => {
    try {
      await axios.put(`${API_BASE}/appointments/${id}/status?status=${status}`);
      fetchAppointments();
    } catch (err) {
      alert('Status update failed: ' + err.message);
    }
  };

  // -----------------------------------------------------------------
  // CHAT & FILE UPLOAD HANDLERS
  // -----------------------------------------------------------------
  const handleSendQuery = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    const userText = inputQuery;
    setInputQuery('');

    const effectivePatient = currentUser.role === 'doctor' ? selectedPatient : null;
    const contextKey = effectivePatient ? effectivePatient.id : 'general';
    const currentSessionId = sessionIds[contextKey] || null;

    const userMsg = { role: 'user', content: userText };
    const updatedMessagesWithUser = [...messages, userMsg];
    setMessages(updatedMessagesWithUser);

    setIsLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, {
        query: userText,
        session_id: currentSessionId,
        patient_id: effectivePatient?.id || null
      });

      if (res.data.session_id) {
        setSessionIds((prev) => ({ ...prev, [contextKey]: res.data.session_id }));
      }

      const botMsg = {
        role: 'assistant',
        content: res.data.response_text,
        report_pdf_url: res.data.report_pdf_url
      };

      const finalMessages = [...updatedMessagesWithUser, botMsg];
      setMessages(finalMessages);
      setPatientSessions((prev) => ({ ...prev, [contextKey]: finalMessages }));
    } catch (err) {
      alert('Chat error: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedPatient) {
      alert('Please select a patient first before uploading OCR documents.');
      return;
    }

    const formData = new FormData();
    formData.append('patient_id', selectedPatient.id);
    formData.append('file', file);
    formData.append('title', file.name);

    setIsLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/ocr/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const contextKey = selectedPatient.id;
      const ocrBotMsg = { 
        role: 'assistant', 
        content: `Document **${file.name}** processed and attached to **${selectedPatient.name}**'s record.`,
        extracted_ocr_content: res.data.content,
        is_safe: true
      };

      const updatedMessages = [...messages, ocrBotMsg];
      setMessages(updatedMessages);
      setPatientSessions((prev) => ({ ...prev, [contextKey]: updatedMessages }));
      fetchPatients();
    } catch (err) {
      alert('OCR Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsLoading(false);
    }
  };

  const filteredPatients = patients.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.owner_name && p.owner_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (p.breed && p.breed.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // =================================================================
  // RENDER LOGIN / REGISTER PAGE
  // =================================================================
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 rounded-3xl p-8 max-w-md w-full shadow-xl space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-2xl text-white mx-auto flex items-center justify-center font-bold shadow-md" style={{ backgroundColor: '#3B6255' }}>
              <Cat className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              {isSigningUp ? 'Create VetMind Account' : 'Welcome to VetMind AI'}
            </h2>
            <p className="text-xs text-gray-500">
              {isSigningUp ? 'Fill details to create your account' : 'Sign in with your email and password'}
            </p>
          </div>

          {/* ROLE SELECTOR TOGGLE */}
          <div className="flex bg-gray-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setSelectedRole('owner')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                selectedRole === 'owner' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
              }`}
            >
              🐾 Pet Owner
            </button>
            <button
              type="button"
              onClick={() => setSelectedRole('doctor')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                selectedRole === 'doctor' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500'
              }`}
            >
              🩺 Veterinary Doctor
            </button>
          </div>

          {/* AUTH FORM */}
          <form onSubmit={handleAuthSubmit} className="space-y-4">
            {isSigningUp && (
              <div>
                <label className="text-xs font-semibold text-gray-700">Full Name</label>
                <input 
                  type="text" required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Dr. John Smith"
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none focus:border-[#3B6255] text-gray-800"
                />
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-gray-700">Email Address</label>
              <input 
                type="email" required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder={selectedRole === 'doctor' ? "dr.smith@vetmind.com" : "owner@gmail.com"}
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none focus:border-[#3B6255] text-gray-800"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700">Password</label>
              <input 
                type="password" required
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none focus:border-[#3B6255] text-gray-800"
              />
            </div>

            <button 
              type="submit"
              className="w-full py-2.5 text-white rounded-xl text-xs font-bold transition-all hover:opacity-90 shadow-md cursor-pointer"
              style={{ backgroundColor: '#3B6255' }}
            >
              {isSigningUp ? 'Create Account' : `Sign In as ${selectedRole === 'doctor' ? 'Doctor' : 'Pet Owner'}`}
            </button>

            {/* TOGGLE LINK */}
            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => setIsSigningUp(!isSigningUp)}
                className="text-xs font-semibold text-[#3B6255] hover:underline cursor-pointer"
              >
                {isSigningUp ? 'Already have an account? Sign In' : "Don't have an account? Create Account"}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // =================================================================
  // MAIN DASHBOARD
  // =================================================================
  return (
    <div className="flex flex-col h-screen font-sans bg-white text-gray-800">
      
      {/* NAVBAR */}
      <header className="h-15 border-b border-gray-200 px-6 flex items-center justify-between sticky top-0 z-40 bg-white">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl text-white flex items-center justify-center font-bold shadow-xs" style={{ backgroundColor: '#3B6255' }}>
              <Cat className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-sm text-gray-900">VetMind AI</span>
              <span className="text-[10px] text-gray-500 uppercase font-semibold block">
                {currentUser.role === 'doctor' ? '🩺 Clinical Portal' : '🐾 Owner Care Portal'}
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-1 border border-gray-200 p-1 rounded-xl">
            {/* WORKSPACE TAB */}
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'chat' ? 'text-white shadow-xs' : 'text-gray-600'
              }`}
              style={{ backgroundColor: activeTab === 'chat' ? '#3B6255' : 'transparent' }}
            >
              <MessageSquare className="w-3.5 h-3.5" /> AI Workspace
            </button>

            {/* DOCTOR-ONLY: PATIENTS DIRECTORY */}
            {currentUser.role === 'doctor' && (
              <button
                onClick={() => setActiveTab('patients')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === 'patients' ? 'text-white shadow-xs' : 'text-gray-600'
                }`}
                style={{ backgroundColor: activeTab === 'patients' ? '#3B6255' : 'transparent' }}
              >
                <Users className="w-3.5 h-3.5" /> Patients Directory
              </button>
            )}

            {/* BOOKINGS TAB */}
            <button
              onClick={() => setActiveTab('bookings')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'bookings' ? 'text-white shadow-xs' : 'text-gray-600'
              }`}
              style={{ backgroundColor: activeTab === 'bookings' ? '#3B6255' : 'transparent' }}
            >
              <Calendar className="w-3.5 h-3.5" /> 
              {currentUser.role === 'doctor' ? 'Manage Appointments' : 'Book Appointment'}
            </button>
          </nav>
        </div>

        {/* ADD PATIENT BUTTON FOR DOCTORS IN DIRECTORY */}
        <div className="flex items-center gap-3">
          {activeTab === 'patients' && currentUser.role === 'doctor' && (
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-white text-xs font-bold rounded-lg transition-all shadow-xs active:scale-95 hover:opacity-90 cursor-pointer"
              style={{ backgroundColor: '#3B6255' }}
            >
              <Plus className="w-4 h-4 text-white" /> Add Patient
            </button>
          )}

          {/* USER PROFILE & LOGOUT */}
          <div className="text-right">
            <span className="text-xs font-bold text-gray-900 block">{currentUser.full_name}</span>
            <span className="text-[10px] text-gray-500 font-mono">{currentUser.email}</span>
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors cursor-pointer"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* BODY CONTENT */}
      <div className="flex-1 overflow-hidden">
        
        {/* VIEW 1: AI WORKSPACE */}
        {activeTab === 'chat' && (
          <div className="flex flex-col h-full max-w-4xl mx-auto px-4">
            
            {/* DOCTOR ONLY: Patient Selector Strip */}
            {currentUser.role === 'doctor' ? (
              <div className="py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-x-auto py-1 no-scrollbar">
                  <span className="text-xs font-semibold text-gray-600 flex items-center gap-1">
                    <FolderOpen className="w-3.5 h-3.5 text-[#3B6255]" /> Context:
                  </span>
                  <button
                    onClick={() => handlePatientSelect(null)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold border cursor-pointer ${
                      selectedPatient === null ? 'bg-[#3B6255] text-white' : 'text-gray-700'
                    }`}
                  >
                    General Reference
                  </button>
                  {patients.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handlePatientSelect(p)}
                      className={`px-3 py-1 rounded-full text-xs font-semibold border cursor-pointer ${
                        selectedPatient?.id === p.id ? 'bg-[#3B6255] text-white' : 'text-gray-700'
                      }`}
                    >
                      {p.name} #{p.id}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* OWNER VIEW: Restricted to AI Clinical Reference Mode */
              <div className="py-3 border-b border-gray-200 flex items-center justify-between bg-emerald-50/50 px-4 rounded-b-2xl">
                <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-[#3B6255]" />
                  Pet Owner Mode: AI Clinical Reference Assistance
                </span>
              </div>
            )}

            {/* Chat Thread */}
            <div className="flex-1 overflow-y-auto py-6 space-y-6">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 my-auto text-gray-600">
                  <div className="w-12 h-12 rounded-2xl border border-gray-200 flex items-center justify-center shadow-xs" style={{ backgroundColor: '#3B625510' }}>
                    <Sparkles className="w-6 h-6" style={{ color: '#3B6255' }} />
                  </div>
                  <div className="space-y-1.5 max-w-sm">
                    <h3 className="text-sm font-bold text-gray-900">VetMind Assistant Ready</h3>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {currentUser.role === 'doctor' && selectedPatient
                        ? `Currently analyzing medical history for ${selectedPatient.name}. Ask questions or attach OCR notes.`
                        : 'Ask general veterinary clinical questions or request pet guidance.'}
                    </p>
                  </div>
                </div>
              ) : (
                messages.map((m, idx) => (
                  <div key={idx} className={`flex gap-3.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {m.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-xl text-white flex items-center justify-center shrink-0 shadow-xs" style={{ backgroundColor: '#3B6255' }}>
                        <Cat className="w-4 h-4" />
                      </div>
                    )}
                    <div className={`max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed border ${
                      m.role === 'user' ? 'bg-[#3B6255] text-white' : 'bg-gray-50 border-gray-200 text-gray-800'
                    }`}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>

                      {/* COLLAPSIBLE RAW EXTRACTED OCR TEXT BOX */}
                      {m.extracted_ocr_content && (
                        <details className="mt-3 border border-gray-200 rounded-xl bg-white overflow-hidden shadow-2xs group">
                          <summary className="px-4 py-2.5 text-xs font-bold text-[#3B6255] bg-gray-100/70 cursor-pointer hover:bg-gray-100 transition-colors flex items-center justify-between list-none">
                            <span className="flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-[#3B6255]" />
                              View Raw Extracted OCR Clinical Notes
                            </span>
                            <ChevronDown className="w-3.5 h-3.5 text-[#3B6255] transition-transform group-open:rotate-180" />
                          </summary>
                          <div className="p-4 text-xs font-mono bg-gray-50 text-gray-800 border-t border-gray-200 max-h-60 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                            {m.extracted_ocr_content}
                          </div>
                        </details>
                      )}

                      {/* PDF Report Download Link */}
                      {m.report_pdf_url && (
                        <div className="mt-4 pt-3 border-t border-gray-200 flex items-center justify-between bg-emerald-50/50 p-3 rounded-xl border-emerald-100">
                          <div className="flex items-center gap-2 text-emerald-900 text-xs font-semibold">
                            <FileText className="w-4 h-4 text-[#3B6255]" />
                            <span>Clinical Summary Report Ready (.pdf)</span>
                          </div>
                          
                          <a 
                            href={`${API_BASE}${m.report_pdf_url}`}
                            target="_blank"
                            rel="noreferrer"
                            download
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-white rounded-lg text-xs font-bold transition-all hover:opacity-90 shadow-xs cursor-pointer"
                            style={{ backgroundColor: '#3B6255' }}
                          >
                            <span>Download PDF</span>
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="flex items-center gap-2 text-xs font-bold text-[#3B6255]">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Processing clinical query...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input Bar */}
            <div className="pb-6">
              <form onSubmit={handleSendQuery} className="flex items-center gap-2 border border-gray-300 rounded-2xl p-2">
                {currentUser.role === 'doctor' && (
                  <>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      onChange={handleFileUpload} 
                      className="hidden" 
                      accept=".pdf,.png,.jpg,.jpeg"
                    />
                    <button 
                      type="button" 
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2.5 hover:bg-gray-100 transition-colors rounded-xl cursor-pointer"
                      style={{ color: '#3B6255' }}
                      title="Attach OCR Clinical Document"
                    >
                      <Paperclip className="w-4 h-4" />
                    </button>
                  </>
                )}

                <input 
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  placeholder={currentUser.role === 'doctor' && selectedPatient ? `Ask about ${selectedPatient.name}'s history...` : "Ask a veterinary health question..."}
                  className="flex-1 bg-transparent border-none text-sm focus:outline-none px-2"
                />
                <button type="submit" disabled={isLoading || !inputQuery.trim()} className="p-2.5 text-white rounded-xl cursor-pointer disabled:opacity-40" style={{ backgroundColor: '#3B6255' }}>
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>

          </div>
        )}

        {/* VIEW 2: DOCTOR-ONLY PATIENTS DIRECTORY */}
        {activeTab === 'patients' && currentUser.role === 'doctor' && (
          <div className="h-full max-w-6xl mx-auto p-8 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Patient Database</h2>
                <p className="text-xs text-gray-500">Manage electronic health records stored in SQLite</p>
              </div>

              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#3B6255]" />
                <input 
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search records..."
                  className="w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-[#3B6255]"
                />
              </div>
            </div>

            <div className="border border-gray-200 rounded-2xl overflow-hidden shadow-xs bg-white">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-gray-200 uppercase tracking-wider font-bold bg-gray-50 text-gray-700">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Patient Name</th>
                    <th className="px-5 py-3.5">Species</th>
                    <th className="px-5 py-3.5">Breed</th>
                    <th className="px-5 py-3.5">Age</th>
                    <th className="px-5 py-3.5">Owner</th>
                    <th className="px-5 py-3.5">Docs</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 text-gray-800">
                  {filteredPatients.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="px-5 py-10 text-center text-gray-400 font-medium">
                        No patient records found in database.
                      </td>
                    </tr>
                  ) : (
                    filteredPatients.map((p) => (
                      <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3.5 font-mono text-gray-400">#{p.id}</td>
                        <td className="px-5 py-3.5 font-bold text-gray-900">{p.name}</td>
                        <td className="px-5 py-3.5">{p.species || 'Feline'}</td>
                        <td className="px-5 py-3.5 text-gray-500">{p.breed || '—'}</td>
                        <td className="px-5 py-3.5 text-gray-500">{p.age || '—'}</td>
                        <td className="px-5 py-3.5 text-gray-500">{p.owner_name || '—'}</td>
                        <td className="px-5 py-3.5">
                          <button
                            onClick={() => setViewingPatientRecords(p)}
                            className="px-2 py-0.5 border border-[#3B6255]/30 text-[#3B6255] bg-[#3B6255]/5 hover:bg-[#3B6255]/15 rounded text-[11px] font-mono font-bold cursor-pointer transition-colors inline-flex items-center gap-1"
                          >
                            <span>{p.records?.length || 0} Docs</span>
                            <Eye className="w-3 h-3 text-[#3B6255]" />
                          </button>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                handlePatientSelect(p);
                                setActiveTab('chat');
                              }}
                              className="px-2.5 py-1 text-white rounded-lg text-[11px] font-bold shadow-2xs cursor-pointer hover:opacity-90"
                              style={{ backgroundColor: '#3B6255' }}
                            >
                              Open Workspace
                            </button>

                            <button
                              onClick={() => setEditingPatient(p)}
                              className="p-1.5 text-gray-600 hover:text-[#3B6255] hover:bg-gray-100 rounded-lg cursor-pointer border border-gray-200"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>

                            <button
                              onClick={() => handleDeletePatient(p.id, p.name)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg cursor-pointer border border-gray-200"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* VIEW 3: BOOKING SECTION */}
        {activeTab === 'bookings' && (
          <div className="h-full max-w-5xl mx-auto p-8 overflow-y-auto space-y-8">
            
            {/* OWNER BOOKING FORM */}
            {currentUser.role === 'owner' && (
              <div className="max-w-lg mx-auto bg-white border border-gray-200 rounded-3xl p-6 shadow-xs space-y-4">
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-[#3B6255]" /> Book Veterinary Appointment
                </h2>
                <form onSubmit={handleCreateBooking} className="space-y-3.5">
                  <div>
                    <label className="text-xs font-semibold text-gray-700">Owner Full Name</label>
                    <input 
                      type="text" required
                      value={newBooking.owner_name}
                      onChange={(e) => setNewBooking({ ...newBooking, owner_name: e.target.value })}
                      placeholder="e.g. Sarah Khan"
                      className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-[#3B6255]"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-700">Pet Name</label>
                      <input 
                        type="text" required
                        value={newBooking.pet_name}
                        onChange={(e) => setNewBooking({ ...newBooking, pet_name: e.target.value })}
                        placeholder="e.g. Leo"
                        className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-[#3B6255]"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-700">Species</label>
                      <select 
                        value={newBooking.species}
                        onChange={(e) => setNewBooking({ ...newBooking, species: e.target.value })}
                        className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none focus:border-[#3B6255]"
                      >
                        <option value="Canine">Canine (Dog)</option>
                        <option value="Feline">Feline (Cat)</option>
                        <option value="Avian">Avian (Bird)</option>
                        <option value="Exotic">Exotic</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-700">Date</label>
                      <input 
                        type="date" required
                        value={newBooking.appointment_date}
                        onChange={(e) => setNewBooking({ ...newBooking, appointment_date: e.target.value })}
                        className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-gray-700">Preferred Time</label>
                      <input 
                        type="text" required
                        value={newBooking.appointment_time}
                        onChange={(e) => setNewBooking({ ...newBooking, appointment_time: e.target.value })}
                        placeholder="e.g. 10:30 AM"
                        className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-gray-700">Reason for Visit</label>
                    <textarea 
                      required rows="3"
                      value={newBooking.reason}
                      onChange={(e) => setNewBooking({ ...newBooking, reason: e.target.value })}
                      placeholder="Describe symptoms or routine checkup reason..."
                      className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                    />
                  </div>
                  <button 
                    type="submit" 
                    className="w-full py-2.5 text-white text-xs font-bold rounded-xl shadow-xs hover:opacity-90 cursor-pointer"
                    style={{ backgroundColor: '#3B6255' }}
                  >
                    Confirm Booking Request
                  </button>
                </form>
              </div>
            )}

            {/* APPOINTMENTS TABLE */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-gray-900">
                {currentUser.role === 'doctor' ? 'Incoming Appointment Requests' : 'Your Booked Appointments'}
              </h3>

              <div className="border border-gray-200 rounded-2xl overflow-hidden bg-white">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-50 border-b border-gray-200 uppercase font-bold text-gray-700">
                    <tr>
                      <th className="px-4 py-3">Pet / Owner</th>
                      <th className="px-4 py-3">Species</th>
                      <th className="px-4 py-3">Schedule</th>
                      <th className="px-4 py-3">Reason</th>
                      <th className="px-4 py-3">Status</th>
                      {currentUser.role === 'doctor' && <th className="px-4 py-3 text-right">Action</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {appointments.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="text-center py-8 text-gray-400">No appointments scheduled yet.</td>
                      </tr>
                    ) : (
                      appointments.map((apt) => (
                        <tr key={apt.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-bold text-gray-900">
                            {apt.pet_name} <span className="text-gray-400 font-normal">({apt.owner_name})</span>
                          </td>
                          <td className="px-4 py-3">{apt.species}</td>
                          <td className="px-4 py-3 font-mono">{apt.appointment_date} at {apt.appointment_time}</td>
                          <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{apt.reason}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              apt.status === 'confirmed' ? 'bg-emerald-100 text-emerald-800' :
                              apt.status === 'cancelled' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                            }`}>
                              {apt.status}
                            </span>
                          </td>
                          {currentUser.role === 'doctor' && (
                            <td className="px-4 py-3 text-right space-x-1">
                              <button 
                                onClick={() => handleUpdateAptStatus(apt.id, 'confirmed')}
                                className="p-1 hover:bg-emerald-50 text-emerald-600 rounded cursor-pointer"
                                title="Confirm Booking"
                              >
                                <CheckCircle2 className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handleUpdateAptStatus(apt.id, 'cancelled')}
                                className="p-1 hover:bg-red-50 text-red-600 rounded cursor-pointer"
                                title="Cancel Booking"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            </td>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

      </div>

      {/* MODAL 1: ADD PATIENT */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="border border-gray-200 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-xl bg-white">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-900">Register Patient Record</h3>
            <form onSubmit={handleCreatePatient} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-gray-700">Patient Name *</label>
                <input 
                  type="text" required
                  value={newPatient.name}
                  onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })}
                  placeholder="e.g. Bella"
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none focus:border-[#3B6255]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700">Species</label>
                  <select
                    value={newPatient.species}
                    onChange={(e) => {
                      const selectedSpecies = e.target.value;
                      const defaultBreed = SPECIES_BREEDS[selectedSpecies]?.[0] || '';
                      setNewPatient({ ...newPatient, species: selectedSpecies, breed: defaultBreed });
                    }}
                    className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none"
                  >
                    {Object.keys(SPECIES_BREEDS).map((species) => (
                      <option key={species} value={species}>{species}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-700">Breed</label>
                  <select
                    value={newPatient.breed}
                    onChange={(e) => setNewPatient({ ...newPatient, breed: e.target.value })}
                    className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-xl text-xs focus:outline-none"
                  >
                    {(SPECIES_BREEDS[newPatient.species] || SPECIES_BREEDS['Feline']).map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700">Age</label>
                  <input 
                    type="text"
                    value={newPatient.age}
                    onChange={(e) => setNewPatient({ ...newPatient, age: e.target.value })}
                    placeholder="e.g. 3 years"
                    className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700">Owner Name</label>
                  <input 
                    type="text"
                    value={newPatient.owner_name}
                    onChange={(e) => setNewPatient({ ...newPatient, owner_name: e.target.value })}
                    placeholder="e.g. Sarah"
                    className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowAddModal(false)} className="flex-1 py-2 border rounded-xl text-xs font-semibold">Cancel</button>
                <button type="submit" className="flex-1 py-2 text-white rounded-xl text-xs font-bold" style={{ backgroundColor: '#3B6255' }}>Save Record</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDIT PATIENT */}
      {editingPatient && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="border border-gray-200 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-xl bg-white">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-900">Edit Patient Record (#{editingPatient.id})</h3>
            <form onSubmit={handleUpdatePatient} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-gray-700">Patient Name *</label>
                <input 
                  type="text" required
                  value={editingPatient.name}
                  onChange={(e) => setEditingPatient({ ...editingPatient, name: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700">Species</label>
                  <select
                    value={editingPatient.species || 'Feline'}
                    onChange={(e) => {
                      const selectedSpecies = e.target.value;
                      const defaultBreed = SPECIES_BREEDS[selectedSpecies]?.[0] || '';
                      setEditingPatient({ ...editingPatient, species: selectedSpecies, breed: defaultBreed });
                    }}
                    className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                  >
                    {Object.keys(SPECIES_BREEDS).map((species) => (
                      <option key={species} value={species}>{species}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-700">Breed</label>
                  <select
                    value={editingPatient.breed || ''}
                    onChange={(e) => setEditingPatient({ ...editingPatient, breed: e.target.value })}
                    className="w-full mt-1 px-3 py-2 border rounded-xl text-xs focus:outline-none"
                  >
                    {(SPECIES_BREEDS[editingPatient.species] || SPECIES_BREEDS['Feline']).map((b) => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setEditingPatient(null)} className="flex-1 py-2 border rounded-xl text-xs font-semibold">Cancel</button>
                <button type="submit" className="flex-1 py-2 text-white rounded-xl text-xs font-bold" style={{ backgroundColor: '#3B6255' }}>Update Record</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: VIEW CLINICAL RECORDS */}
      {viewingPatientRecords && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="border border-gray-200 rounded-2xl p-6 w-full max-w-2xl max-h-[80vh] flex flex-col space-y-4 shadow-xl bg-white">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-900">
                  Extracted Clinical Records — {viewingPatientRecords.name} (#{viewingPatientRecords.id})
                </h3>
              </div>
              <button onClick={() => setViewingPatientRecords(null)} className="p-1 rounded-lg text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {(!viewingPatientRecords.records || viewingPatientRecords.records.length === 0) ? (
                <p className="text-xs text-gray-400 text-center py-10 font-medium">No OCR clinical notes uploaded for this patient yet.</p>
              ) : (
                viewingPatientRecords.records.map((rec) => (
                  <div key={rec.id} className="border border-gray-200 rounded-xl p-4 bg-gray-50 space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold text-gray-900">
                      <span className="flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-[#3B6255]" />
                        {rec.title}
                      </span>
                    </div>
                    <div className="p-3 bg-white border border-gray-200 rounded-lg text-xs font-mono text-gray-800 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                      {rec.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
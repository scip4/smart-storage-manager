import React, { useState, useEffect, useCallback } from 'react';
import { HardDrive, Trash2, Archive, Play, Calendar, Settings, AlertTriangle, Film, Tv, ExternalLink, Check, X, RefreshCw, FileText } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api';

const LoadingSpinner = () => (
  <div className="flex justify-center items-center p-10">
    <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
    <span className="ml-4 text-lg text-gray-600">Loading data...</span>
  </div>
);

const ErrorDisplay = ({ error, onRetry }) => (
    <div className="bg-red-50 border border-red-200 rounded-md p-4 text-center">
      <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
      <h3 className="text-lg font-semibold text-red-800">An Error Occurred</h3>
      <p className="text-red-700 mb-4">{error}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
      >
        Try Again
      </button>
    </div>
);

const LogViewer = () => {
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/logs`);
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      setLogs("Failed to load logs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          Application Logs
        </h2>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center disabled:bg-gray-400"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>
      <div className="bg-gray-900 text-white font-mono text-xs rounded p-4 h-96 overflow-y-scroll">
        <pre>
          {loading ? 'Loading logs...' : logs}
        </pre>
      </div>
      <p className="text-xs text-gray-500 mt-2">Displaying the last 200 lines of the log file.</p>
    </div>
  );
};


const SmartStorageManager = () => {
  // Data State
  const [storageData, setStorageData] = useState({ total: 0, used: 0, available: 0 });
  const [allContent, setAllContent] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [potentialSavings, setPotentialSavings] = useState(0);
  const [libraryStats, setLibraryStats] = useState({});
  const [upcomingReleases, setUpcomingReleases] = useState([]);
  const [settings, setSettings] = useState({});
  const [connectionStatus, setConnectionStatus] = useState({});

  // UI State
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [contentFilter, setContentFilter] = useState('all');
  const [streamingFilter, setStreamingFilter] = useState('all');

  // Data Fetching Logic
  const fetchDataForTab = useCallback(async (tab) => {
    if (tab === 'logs') return; // The LogViewer handles its own fetching
    setLoading(true);
    setError(null);
    try {
        let response;
        switch (tab) {
            case 'dashboard':
                response = await fetch(`${API_BASE_URL}/dashboard`);
                if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
                const dashData = await response.json();
                setStorageData(dashData.storageData);
                setCandidates(dashData.candidates);
                setPotentialSavings(dashData.potentialSavings);
                setUpcomingReleases(dashData.upcomingReleases);
                setLibraryStats(dashData.libraryStats);
                break;
            case 'content':
                response = await fetch(`${API_BASE_URL}/content`);
                if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
                setAllContent(await response.json());
                break;
            case 'settings':
                const [settingsRes, statusRes] = await Promise.all([fetch(`${API_BASE_URL}/settings`), fetch(`${API_BASE_URL}/status`)]);
                if (!settingsRes.ok || !statusRes.ok) throw new Error('Failed to fetch settings data.');
                setSettings(await settingsRes.json());
                setConnectionStatus(await statusRes.json());
                break;
            default: break;
        }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDataForTab(activeTab);
  }, [activeTab, fetchDataForTab]);

  // Action Handling
  const executeAction = async (item, action) => {
    try {
      const response = await fetch(`${API_BASE_URL}/content/${item.id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, item }), // Pass the whole item object
      });
      const resData = await response.json();
      if (!response.ok) {
        throw new Error(resData.message || `Failed to perform ${action}.`);
      }
      alert(resData.message);
      fetchDataForTab(activeTab); // Refresh data
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleSaveSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error('Failed to save settings.');
      alert('Settings saved successfully!');
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const Dashboard = () => {
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={() => fetchDataForTab('dashboard')} />;
    
    return (
      <div className="space-y-6">
        {/* Storage Overview */}
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold flex items-center mb-4"><HardDrive className="w-5 h-5 mr-2" />Storage Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center"><div className="text-2xl font-bold text-blue-600">{storageData.used?.toFixed(1)} GB</div><div className="text-gray-600">Used</div></div>
              <div className="text-center"><div className="text-2xl font-bold text-green-600">{storageData.available?.toFixed(1)} GB</div><div className="text-gray-600">Available</div></div>
              <div className="text-center"><div className="text-2xl font-bold text-orange-600">{potentialSavings.toFixed(1)} GB</div><div className="text-gray-600">Potential Savings</div></div>
              <div className="text-center"><div className="text-2xl font-bold text-gray-800">{storageData.total?.toFixed(1)} GB</div><div className="text-gray-600">Total</div></div>
            </div>
        </div>

        {/* Library Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">TV Shows</h3>
                <p className="text-2xl font-bold text-blue-600">{libraryStats.tv || 0} Series / {libraryStats.tv_episodes || 0} Episodes</p>
                <p className="text-sm text-gray-600">{libraryStats.tv_size?.toFixed(1) || '0.0'} GB</p>
              </div>
              <Tv className="w-8 h-8 text-blue-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Movies</h3>
                <p className="text-2xl font-bold text-purple-600">{libraryStats.movies || 0}</p>
                <p className="text-sm text-gray-600">{libraryStats.movies_size?.toFixed(1) || '0.0'} GB</p>
              </div>
              <Film className="w-8 h-8 text-purple-500" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold">On Streaming</h3>
                    <p className="text-2xl font-bold text-green-600">{libraryStats.onStreaming || 0}</p>
                </div>
                <ExternalLink className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        {/* Action Candidates */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Recommended Actions</h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {candidates.map(item => (
              <div key={`${item.type}-${item.id}`} className="flex justify-between items-center p-3 border rounded">
                <div className="flex-1"><div className="font-medium">{item.title}</div><div className="text-sm text-gray-600">{item.size} GB • Last watched: {item.lastWatched || 'Never'}</div></div>
                <div className="flex space-x-2 ml-4">
                  {item.status === 'candidate-delete' && <button onClick={() => executeAction(item, 'delete')} className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 flex items-center"><Trash2 className="w-3 h-3 mr-1" />Delete</button>}
                  {item.status === 'candidate-archive' && <button onClick={() => executeAction(item, 'archive')} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center"><Archive className="w-3 h-3 mr-1" />Archive</button>}
                </div>
              </div>
            ))}
            {candidates.length === 0 && <div className="text-center text-gray-500 py-4">No cleanup actions recommended.</div>}
          </div>
        </div>
      </div>
    );
  };
  
  const SettingsPanel = () => {
    // This component remains the same, showing settings and archive path input
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">Connection Status</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* ... Connection status pills ... */}
            </div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">General Settings</h2>
            {/* ... General settings inputs ... */}
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Archive Settings</h2>
            <div>
                <label htmlFor="archive-path" className="block text-sm font-medium mb-2">Archive Folder Path</label>
                <input type="text" id="archive-path" placeholder="/path/to/cold-storage" value={settings.archiveFolderPath || ''} onChange={(e) => setSettings({ ...settings, archiveFolderPath: e.target.value })} className="w-full border rounded px-3 py-2"/>
                <p className="text-xs text-gray-500 mt-1">The full path to the root folder where archived content will be moved.</p>
            </div>
        </div>
        <button onClick={handleSaveSettings} className="w-full bg-blue-500 text-white rounded py-3 hover:bg-blue-600 font-medium">Save All Settings</button>
      </div>
    );
  };

  const ContentManagement = () => (
    <div className="bg-white rounded-lg shadow-md p-6 text-center">
        <h2 className="text-xl font-semibold">Content Management</h2>
        <p className="text-gray-500 mt-4">This section is under construction.</p>
    </div>
  );


  return (
    <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Smart Storage Manager</h1>
        <p className="text-gray-600">Automated Plex, Sonarr, and Radarr library optimization</p>
      </div>

      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'dashboard', name: 'Dashboard', icon: HardDrive },
              { id: 'content', name: 'Content', icon: Play },
              { id: 'logs', name: 'Logs', icon: FileText },
              { id: 'settings', name: 'Settings', icon: Settings }
            ].map(({ id, name, icon: Icon }) => (
              <button key={id} onClick={() => setActiveTab(id)} className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${activeTab === id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
                <Icon className="w-4 h-4 mr-2" />{name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {activeTab === 'dashboard' && <Dashboard />}
      {activeTab === 'content' && <ContentManagement />}
      {activeTab === 'logs' && <LogViewer />}
      {activeTab === 'settings' && <SettingsPanel />}
    </div>
  );
};

export default SmartStorageManager;
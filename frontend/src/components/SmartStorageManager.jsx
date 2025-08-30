import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { HardDrive, Trash2, Archive, Play, Settings, AlertTriangle, Film, Tv, ExternalLink, Check, X, RefreshCw, FileText, Search } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api'; // Use a relative path for production/Docker
const ITEMS_PER_PAGE = 10;

// --- Helper Functions & Components (Defined at the top level) ---

const formatStorage = (gb) => {
  if (gb >= 1000) {
    return (gb / 1000).toFixed(1) + ' TB';
  }
  return (gb || 0).toFixed(1) + ' GB';
};

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
      <p className="text-red-700 mb-4">{error || "Could not connect to the backend."}</p>
      <button onClick={onRetry} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">Try Again</button>
    </div>
);

const InputField = React.memo(({ label, value, onChange, type = "text", placeholder = "" }) => (
    <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
        <input type={type} value={value || ''} onChange={onChange} className="w-full border rounded px-3 py-2" placeholder={placeholder} />
    </div>
));

const ArchiveFolderInput = React.memo(({ folder, index, onUpdate, onDelete }) => (
    <div className="flex items-center">
        <input type="text" value={folder} onChange={(e) => onUpdate(index, e.target.value)} className="flex-1 border rounded px-3 py-1.5 mr-2" />
        <button onClick={() => onDelete(index)} className="text-red-500 hover:text-red-700"><X className="w-4 h-4" /></button>
    </div>
));

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
      setLogs("Failed to load logs. Is the backend running?");
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

const MediaItemCard = ({ item, onRuleChange, onExecuteAction }) => {
    const isCandidate = item.status ? item.status.includes('candidate') : false;

    return (
        <div className={`flex flex-col md:flex-row justify-between items-center p-4 border rounded-lg shadow-sm ${isCandidate ? 'bg-yellow-50 border-yellow-200' : 'bg-white'}`}>
            <div className="flex-1 w-full md:w-auto">
                <div className="flex items-center mb-2">
                    {item.type === 'movie' ? <Film className="w-5 h-5 mr-2 text-purple-500" /> : <Tv className="w-5 h-5 mr-2 text-blue-500" />}
                    <div className="font-bold text-gray-800">{item.title}</div>
                    {item.year && <span className="text-gray-500 ml-2">({item.year})</span>}
                </div>
                <div className="text-sm text-gray-600 mb-2 space-x-4">
                    <span><strong>Size:</strong> {item.size} GB</span>
                    <span><strong>Last Watched:</strong> {item.lastWatched || 'N/A'}</span>
                    <span><strong>Watch Count:</strong> {item.watchCount}</span>
                    <span><strong>Storage Location:</strong> {item.rootFolderPath}</span>
                    <span><strong>Streaming:</strong> {item.streamingServices}</span>
                    
                </div>
                <div className="text-sm text-gray-600">
                    <span><strong>Status:</strong> <span className={`font-medium ${isCandidate ? 'text-yellow-800' : 'text-green-800'}`}>{item.status}</span></span>
                </div>
            </div>
            <div className="flex items-center space-x-3 mt-4 md:mt-0">
                <select
                    value={item.rule}
                    onChange={(e) => onRuleChange(item.id, e.target.value)}
                    className="text-sm border rounded px-2 py-1.5 min-w-[140px] bg-white hover:border-gray-400"
                >
                    <option value="auto-manage">Auto Manage</option>
                    <option value="keep-forever">Keep Forever</option>
                    <option value="archive-after-6months">Archive After 6 Months</option>
                    <option value="delete-after-watched">Delete After Watched</option>
                </select>
                <button onClick={() => onExecuteAction(item, 'archive')} className="p-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200" title="Archive">
                  <Archive className="w-4 h-4" />
                </button>
                <button onClick={() => onExecuteAction(item, 'delete')} className="p-2 bg-red-100 text-red-700 rounded hover:bg-red-200" title="Delete">
                  <Trash2 className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
};

// --- VIEW COMPONENTS (Moved outside the main component) ---

const Dashboard = React.memo(({ loading, error, storageData, archiveData, potentialSavings, libraryStats, candidates, executeAction, onRetry }) => {
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;
    return (
        <div className="space-y-6">
   <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold flex items-center mb-4">
         <HardDrive className="w-5 h-5 mr-2" />
         Storage Overview
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
         <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{formatStorage(storageData.used)}</div>
            <div className="text-gray-600">Main Used</div>
         </div>
         <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{formatStorage(storageData.available)}</div>
            <div className="text-gray-600">Main Available</div>
         </div>

         <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{formatStorage(potentialSavings)}</div>
            <div className="text-gray-600">Potential Savings</div>
         </div>


                        <div className="text-center"><div className="text-2xl font-bold text-gray-800">{formatStorage(archiveData.total)}</div><div className="text-gray-600">Archive Total</div></div>
                        <div className="text-center"><div className="text-2xl font-bold text-purple-600">{formatStorage(archiveData.used)}</div><div className="text-gray-600">Archive Used</div></div>
                        <div className="text-center"><div className="text-2xl font-bold text-black-600">{formatStorage(archiveData.available)}</div><div className="text-gray-600">Archive Available</div></div>   


      </div>
   </div>
   <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="bg-white rounded-lg shadow-md p-6">
         <div className="flex items-center justify-between">
            <div>
               <h3 className="text-lg font-semibold">TV Shows</h3>
               <p className="text-2xl font-bold text-blue-600">{libraryStats.tv || 0} Series / {libraryStats.tv_episodes || 0} Episodes</p>
               <p className="text-sm text-gray-600">{formatStorage(libraryStats.tv_size)}</p>
            </div>
            <Tv className="w-8 h-8 text-blue-500" />
         </div>
      </div>
      <div className="bg-white rounded-lg shadow-md p-6">
         <div className="flex items-center justify-between">
            <div>
               <h3 className="text-lg font-semibold">Movies</h3>
               <p className="text-2xl font-bold text-purple-600">{libraryStats.movies || 0}</p>
               <p className="text-sm text-gray-600">{formatStorage(libraryStats.movies_size)}</p>
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
   <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Recommended Actions</h3>
      <div className="space-y-3 max-h-96 overflow-y-auto">
         {candidates.length > 0 ? candidates.map(item => (
         <div key={`${item.type}-${item.id}`} className="flex justify-between items-center p-3 border rounded">
            <div className="flex-1">
<               div className="font-medium">{item.title}</div>
               <div className="text-sm text-gray-600">{item.size} GB &bull; {item.reason}</div>
               <div className="text-sm text-gray-600">{item.filePath}</div>
               <div className="text-sm text-gray-600">{item.streamingServices}</div>
            </div>
            <div className="flex space-x-2 ml-4">
               {item.status.includes('delete') && 
               <button onClick={() =>
                  executeAction(item, 'delete')} className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 flex items-center">
                  <Trash2 className="w-3 h-3 mr-1" />
                  Delete
               </button>
               }{item.status.includes('archive') && 
               <button onClick={() =>
                  executeAction(item, 'archive')} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center">
                  <Archive className="w-3 h-3 mr-1" />
                  Archive
               </button>
               }
            </div>
         </div>
         )) : 
         <div className="text-center text-gray-500 py-4">No cleanup actions recommended.</div>
         }
      </div>
   </div>
</div>
    );
});

const ContentManagement = React.memo(({ loading, error, allContent, executeAction, onRetry }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [contentFilter, setContentFilter] = useState('all');
    const [sortBy, setSortBy] = useState('size-desc');
    const [currentPage, setCurrentPage] = useState(1);

    const processedContent = useMemo(() => {
        let filtered = allContent || [];
        if (contentFilter === 'tv') filtered = filtered.filter(item => item.type === 'tv');
        if (contentFilter === 'movies') filtered = filtered.filter(item => item.type === 'movie');
        if (searchTerm) { filtered = filtered.filter(item => item.title.toLowerCase().includes(searchTerm.toLowerCase())); }
        filtered.sort((a, b) => { const [field, dir] = sortBy.split('-'); const mod = dir === 'asc' ? 1 : -1; if (field === 'title') return a.title.localeCompare(b.title) * mod; if (field === 'size') return (a.size - b.size) * mod; return 0; });
        return filtered;
    }, [allContent, contentFilter, searchTerm, sortBy]);

    const totalPages = Math.ceil(processedContent.length / ITEMS_PER_PAGE);
    const paginatedItems = processedContent.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

    useEffect(() => { setCurrentPage(1); }, [contentFilter, searchTerm, sortBy]);

    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-4 flex flex-col md:flex-row gap-4 items-center"><div className="relative flex-grow w-full md:w-auto"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" /><input type="text" placeholder="Search by title..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full border rounded-lg px-10 py-2" /></div><div className="flex gap-4 w-full md:w-auto"><select value={contentFilter} onChange={(e) => setContentFilter(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 bg-white"><option value="all">All Content</option><option value="tv">TV Shows</option><option value="movies">Movies</option></select><select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 bg-white"><option value="size-desc">Sort by Size (High-Low)</option><option value="size-asc">Sort by Size (Low-High)</option><option value="title-asc">Sort by Title (A-Z)</option></select></div></div>
            <div className="space-y-3">{paginatedItems.length > 0 ? paginatedItems.map(item => (<MediaItemCard key={`${item.type}-${item.id}`} item={item} onRuleChange={() => {}} onExecuteAction={executeAction} />)) : <div className="text-center text-gray-500 py-16 bg-white rounded-lg shadow-md"><p className="text-lg">No content found matching your criteria.</p></div>}</div>
            {totalPages > 1 && (<div className="flex justify-between items-center bg-white rounded-lg shadow-md p-4"><button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-4 py-2 bg-gray-200 text-gray-800 rounded disabled:opacity-50">Previous</button><span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span><button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-4 py-2 bg-gray-200 text-gray-800 rounded disabled:opacity-50">Next</button></div>)}
        </div>
    );
});

const SettingsPanel = React.memo(({ loading, error, connectionStatus, formSettings, onFieldChange, onAddFolder, onUpdateFolder, onDeleteFolder, onSave, onRetry, onStreamingProviderChange }) => {
    // Add a new state to manage the sync button's status
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState('');

    const handleManualSync = async () => {
        setIsSyncing(true);
        setSyncMessage(''); // Clear previous messages
        try {
            const response = await fetch(`${API_BASE_URL}/sync/trigger`, { method: 'POST' });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Failed to start sync.');
            }
            
            setSyncMessage(data.message);
            // Hide the success message after a few seconds
            setTimeout(() => setSyncMessage(''), 5000);

        } catch (err) {
            setSyncMessage(`Error: ${err.message}`);
        } finally {
            // We set a timeout here to prevent the user from spamming the button
            setTimeout(() => setIsSyncing(false), 3000);
        }
    };    
    
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorDisplay error={error} onRetry={onRetry} />;
    
    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6"><h3 className="text-lg font-semibold mb-4">Connection Status</h3><div className="grid grid-cols-1 md:grid-cols-3 gap-4">{Object.entries(connectionStatus).map(([service, status]) => (<div key={service} className={`p-3 border rounded ${status === 'Connected' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}><div className={`font-medium ${status === 'Connected' ? 'text-green-800' : 'text-red-800'}`}>{service.charAt(0).toUpperCase() + service.slice(1)}: {status}</div></div>))}</div></div>
            
             {/* --- NEW MANUAL SYNC SECTION --- */}
            <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex flex-col md:flex-row justify-between items-center">
                    <div>
                        <h3 className="text-lg font-semibold">Manual Data Sync</h3>
                        <p className="text-sm text-gray-500 mt-1">
                            Force the application to immediately refresh all data from Plex, Sonarr, and Radarr.
                        </p>
                    </div>
                    <div className="mt-4 md:mt-0">
                        <button
                            onClick={handleManualSync}
                            disabled={isSyncing}
                            className="px-6 py-2 bg-green-500 text-white font-semibold rounded-lg shadow-md hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                        >
                            <RefreshCw className={`w-5 h-5 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
                            {isSyncing ? 'Syncing...' : 'Start Manual Sync'}
                        </button>
                    </div>
                </div>
                {syncMessage && (
                    <p className={`text-sm mt-4 text-center p-2 rounded ${syncMessage.startsWith('Error:') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                        {syncMessage}
                    </p>
                )}
            </div>
            
            
            
            <div className="bg-white rounded-lg shadow-md p-6"><h2 className="text-xl font-semibold mb-4">Environment Variables</h2><h1>Restart for changes to take affect.</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6"><div className="space-y-4"><h3 className="text-lg font-semibold">Data Update Interval</h3>
            <InputField label="Update Intrerval" value={formSettings.DATA_UPDATE_INTERVAL} onChange={onFieldChange('DATA_UPDATE_INTERVAL')} />
            </div>
            
            </div>
            
            
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6"><div className="space-y-4"><h3 className="text-lg font-semibold">Plex</h3>
            <InputField label="Plex URL" value={formSettings.PLEX_URL} onChange={onFieldChange('PLEX_URL')} />
            <InputField label="Plex Token" type="password" value={formSettings.PLEX_TOKEN} onChange={onFieldChange('PLEX_TOKEN')} /></div>
            <div className="space-y-4"><h3 className="text-lg font-semibold">Sonarr</h3><InputField label="Sonarr URL" value={formSettings.SONARR_URL} onChange={onFieldChange('SONARR_URL')} /><InputField label="Sonarr API Key" type="password" value={formSettings.SONARR_API_KEY} onChange={onFieldChange('SONARR_API_KEY')} /></div><div className="space-y-4"><h3 className="text-lg font-semibold">Radarr</h3><InputField label="Radarr URL" value={formSettings.RADARR_URL} onChange={onFieldChange('RADARR_URL')} /><InputField label="Radarr API Key" type="password" value={formSettings.RADARR_API_KEY} onChange={onFieldChange('RADARR_API_KEY')} /></div><div className="space-y-4"><h3 className="text-lg font-semibold">Other</h3><InputField label="Mount Points" placeholder="/data/media, /data/downloads" value={formSettings.MOUNT_POINTS?.join(', ') || ''} onChange={onFieldChange('MOUNT_POINTS', true)} /></div></div><div className="mt-8"><h3 className="text-lg font-semibold mb-4">Archive Folders</h3><div className="mb-6"><h3 className="text-lg font-semibold mb-2">TV Shows</h3><div className="space-y-2">{formSettings.TV_ARCHIVE_FOLDERS?.map((folder, index) => (<ArchiveFolderInput key={`tv-${index}`} folder={folder} index={index} onUpdate={(idx, val) => onUpdateFolder('TV_ARCHIVE_FOLDERS', idx, val)} onDelete={(idx) => onDeleteFolder('TV_ARCHIVE_FOLDERS', idx)} />))}{(!formSettings.TV_ARCHIVE_FOLDERS || formSettings.TV_ARCHIVE_FOLDERS.length === 0) && (<p className="text-gray-500">No TV archive folders</p>)}<button onClick={() => onAddFolder('TV_ARCHIVE_FOLDERS')} className="mt-2 px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200">+ Add</button></div></div><div className="mb-6"><h3 className="text-lg font-semibold mb-2">Movies</h3><div className="space-y-2">{formSettings.MOVIE_ARCHIVE_FOLDERS?.map((folder, index) => (<ArchiveFolderInput key={`mv-${index}`} folder={folder} index={index} onUpdate={(idx, val) => onUpdateFolder('MOVIE_ARCHIVE_FOLDERS', idx, val)} onDelete={(idx) => onDeleteFolder('MOVIE_ARCHIVE_FOLDERS', idx)} />))}{(!formSettings.MOVIE_ARCHIVE_FOLDERS || formSettings.MOVIE_ARCHIVE_FOLDERS.length === 0) && (<p className="text-gray-500">No movie archive folders</p>)}<button onClick={() => onAddFolder('MOVIE_ARCHIVE_FOLDERS')} className="mt-2 px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200">+ Add</button></div></div></div>
            
            
            
                        {/* --- NEW STREAMING PREFERENCES SECTION --- */}
            <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <ExternalLink className="w-5 h-5 mr-2" />
                    Streaming Preferences
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">
                            Monitor these streaming services:
                        </label>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {(formSettings.availableStreamingProviders || []).map(provider => (
                                <label key={provider} className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        checked={(formSettings.STREAMING_PROVIDERS || []).includes(provider)}
                                        onChange={(e) => onStreamingProviderChange(provider, e.target.checked)}
                                    />
                                    <span className="text-sm text-gray-700">{provider}</span>
                                </label>
                            ))}
                        </div>
                        {(!formSettings.availableStreamingProviders || formSettings.availableStreamingProviders.length === 0) && (
                            <p className="text-sm text-gray-500 mt-2">No streaming providers configured in the backend .env file.</p>
                        )}
                    </div>
                </div>
            </div>
            
            
            
            
            
            
            
            
            <button onClick={onSave} className="w-full bg-blue-500 text-white rounded py-3 hover:bg-blue-600 font-medium">Save All Settings</button></div>
        
        

        
        
        
        
        
        
        
        
        </div>
    );
});


// --- MAIN PARENT COMPONENT ---

const SmartStorageManager = () => {
    // Data State
    const [storageData, setStorageData] = useState({});
    const [archiveData, setArchiveData] = useState({});
    const [allContent, setAllContent] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [libraryStats, setLibraryStats] = useState({});
    const [settings, setSettings] = useState({});
    const [potentialSavings, setPotentialSavings] = useState(0);
    // UI State
    const [activeTab, setActiveTab] = useState('dashboard');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
    const [archiveFolders, setArchiveFolders] = useState([]);
    const [selectedArchiveFolder, setSelectedArchiveFolder] = useState('');
    const [currentArchiveItem, setCurrentArchiveItem] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState({});
    // Form state for settings page
    const [formSettings, setFormSettings] = useState({});
    
    // Sync form state when settings are loaded
    useEffect(() => {
        if (Object.keys(settings).length > 0) {
            setFormSettings(settings);
        }
    }, [settings]);

    const fetchDataForTab = useCallback(async (tab) => {
        if (tab === 'logs') return;
        setLoading(true);
        setError(null);
        try {
            let response;
            switch (tab) {
                case 'dashboard':
                    response = await fetch(`${API_BASE_URL}/dashboard`);
                    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                    const dashData = await response.json();
                    setStorageData(dashData.storageData);
                    setArchiveData(dashData.archiveData);
                    setCandidates(dashData.candidates);
                    setPotentialSavings(dashData.potentialSavings);
                    setLibraryStats(dashData.libraryStats);
                    break;
                case 'content':
                    response = await fetch(`${API_BASE_URL}/content`);
                    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
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
        } catch (err) { setError(err.message); } finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchDataForTab(activeTab); }, [activeTab, fetchDataForTab]);

    const fetchRootFolders = useCallback(async (type) => {
        try {
            const response = await fetch(`${API_BASE_URL}/root-folders?type=${type}`);
            const data = await response.json();
            if (response.ok) {
                setArchiveFolders(data.folders);
                if (data.folders.length > 0) { setSelectedArchiveFolder(data.folders[0].path); }
            } else { throw new Error(data.message || 'Failed to fetch root folders'); }
        } catch (err) { alert(`Error: ${err.message}`); }
    }, []);

    const openArchiveDialog = useCallback((item) => {
        setCurrentArchiveItem(item);
        setIsArchiveDialogOpen(true);
        fetchRootFolders(item.type === 'tv' ? 'sonarr' : 'radarr');
    }, [fetchRootFolders]);

    const handleArchiveConfirm = useCallback(async () => {
        if (!currentArchiveItem || !selectedArchiveFolder) return;
        try {
            const response = await fetch(`${API_BASE_URL}/content/${currentArchiveItem.id}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'archive', item: currentArchiveItem, archivePath: selectedArchiveFolder }),
            });
            const resData = await response.json();
            if (!response.ok) { throw new Error(resData.message || `Failed to perform archive.`); }
            alert(resData.message);
            fetchDataForTab(activeTab);
        } catch (err) { alert(`Error: ${err.message}`); }
        finally { setIsArchiveDialogOpen(false); }
    }, [currentArchiveItem, selectedArchiveFolder, activeTab, fetchDataForTab]);

    const executeAction = useCallback((item, action) => {
        if (action === 'archive') {
            openArchiveDialog(item);
        } else if (action === 'delete') {
            const confirmDelete = window.confirm(`Are you sure you want to delete "${item.title}"? This cannot be undone.`);
            if (confirmDelete) {
                // Perform the delete action
                (async () => {
                    try {
                        const response = await fetch(`${API_BASE_URL}/content/${item.id}/action`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, item }), });
                        const resData = await response.json();
                        if (!response.ok) { throw new Error(resData.message || `Failed to perform ${action}.`); }
                        alert(resData.message);
                        fetchDataForTab(activeTab);
                    } catch (err) { alert(`Error: ${err.message}`); }
                })();
            }
        }
    }, [activeTab, fetchDataForTab, openArchiveDialog]);

    const handleSaveSettings = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formSettings) });
            if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.message || 'Failed to save settings.'); }
            alert('Settings saved successfully!');
            fetchDataForTab('settings');
        } catch (err) { alert(`Error: ${err.message}`); }
    }, [formSettings, fetchDataForTab]);
    
    const handleFieldChange = useCallback((field, isArray = false) => (e) => {
        const value = isArray ? e.target.value.split(',').map(s => s.trim()) : e.target.value;
        setFormSettings(prev => ({ ...prev, [field]: value }));
    }, []);

        // --- NEW HANDLER for Streaming Provider Checkboxes ---
    const handleStreamingProviderChange = useCallback((provider, isChecked) => {
        setFormSettings(prev => {
            const currentServices = prev.STREAMING_PROVIDERS || [];
            let newServices;
            if (isChecked) {
                // Add the provider, ensuring no duplicates
                newServices = [...new Set([...currentServices, provider])];
            } else {
                // Remove the provider
                newServices = currentServices.filter(s => s !== provider);
            }
            return { ...prev, STREAMING_PROVIDERS: newServices };
        });
    }, []);



    const handleAddFolder = useCallback((folderType) => {
        setFormSettings(prev => ({ ...prev, [folderType]: [...(prev[folderType] || []), ''] }));
    }, []);

    const handleUpdateFolder = useCallback((folderType, index, value) => {
        setFormSettings(prev => { const folders = [...(prev[folderType] || [])]; folders[index] = value; return { ...prev, [folderType]: folders }; });
    }, []);

    const handleDeleteFolder = useCallback((folderType, index) => {
        setFormSettings(prev => { const folders = [...(prev[folderType] || [])]; folders.splice(index, 1); return { ...prev, [folderType]: folders }; });
    }, []);

    return (
        <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
            <div className="mb-6"><h1 className="text-3xl font-bold text-gray-800">Smart Storage Manager</h1><p className="text-gray-600">Automated Plex, Sonarr, and Radarr library optimization</p></div>
            <div className="mb-6"><div className="border-b border-gray-200"><nav className="-mb-px flex space-x-8">
                {[ { id: 'dashboard', name: 'Dashboard', icon: HardDrive }, { id: 'content', name: 'Content', icon: Play }, { id: 'logs', name: 'Logs', icon: FileText }, { id: 'settings', name: 'Settings', icon: Settings }].map(({ id, name, icon: Icon }) => (<button key={id} onClick={() => setActiveTab(id)} className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${activeTab === id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}><Icon className="w-4 h-4 mr-2" />{name}</button>))}
            </nav></div></div>
            {activeTab === 'dashboard' && <Dashboard loading={loading} error={error} storageData={storageData} archiveData={archiveData} potentialSavings={potentialSavings} libraryStats={libraryStats} candidates={candidates} executeAction={executeAction} onRetry={() => fetchDataForTab('dashboard')} />}
            {activeTab === 'content' && <ContentManagement loading={loading} error={error} allContent={allContent} executeAction={executeAction} onRetry={() => fetchDataForTab('content')} />}
            {activeTab === 'logs' && <LogViewer />}
            {activeTab === 'settings' && <SettingsPanel loading={loading} error={error} connectionStatus={connectionStatus} formSettings={formSettings} onFieldChange={handleFieldChange} onAddFolder={handleAddFolder} onUpdateFolder={handleUpdateFolder} onDeleteFolder={handleDeleteFolder} onSave={handleSaveSettings} // --- Pass the new handler down as a prop ---
                    onStreamingProviderChange={handleStreamingProviderChange} onRetry={() => fetchDataForTab('settings')} />}

            {isArchiveDialogOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold mb-4">Select Archive Folder</h2>
                        <select className="w-full border rounded px-3 py-2 mb-4" value={selectedArchiveFolder} onChange={(e) => setSelectedArchiveFolder(e.target.value)}>
                            {archiveFolders.map(folder => (<option key={folder.path} value={folder.path}>{folder.path}</option>))}
                        </select>
                        <div className="flex justify-end space-x-3">
                            <button className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300" onClick={() => setIsArchiveDialogOpen(false)}>Cancel</button>
                            <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" onClick={handleArchiveConfirm}>Archive</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SmartStorageManager;
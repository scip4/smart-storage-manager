import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { HardDrive, Trash2, Archive, Play, Calendar, Settings, AlertTriangle, Film, Tv, ExternalLink, Check, X, RefreshCw, FileText, Search } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api';
const ITEMS_PER_PAGE = 10;

// --- Helper Components ---

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

// --- Main Application Component ---

const SmartStorageManager = () => {
    // Data State
    const [storageData, setStorageData] = useState({ total: 0, used: 0, available: 0 });
    const [allContent, setAllContent] = useState([]);
    const [candidates, setCandidates] = useState([]);
    const [endedShows, setEndedShows] = useState([]);
    const [streamingMovies, setStreamingMovies] = useState([]);
    const [potentialSavings, setPotentialSavings] = useState(0);
    const [libraryStats, setLibraryStats] = useState({});
    const [upcomingReleases, setUpcomingReleases] = useState([]);
    const [settings, setSettings] = useState({});
    const [connectionStatus, setConnectionStatus] = useState({});
    const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
    const [archiveFolders, setArchiveFolders] = useState([]);
    const [selectedArchiveFolder, setSelectedArchiveFolder] = useState('');
    const [currentArchiveItem, setCurrentArchiveItem] = useState(null);

    // UI State
    const [activeTab, setActiveTab] = useState('dashboard');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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
                    setEndedShows(dashData.recommendedActions?.endedShows || []);
                    setStreamingMovies(dashData.recommendedActions?.streamingMovies || []);
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
                    //setSettings(await settingsRes.json());
                    //setConnectionStatus(await statusRes.json());
                    break;
                default: break;
            }
        } catch (err) { setError(err.message); } finally { setLoading(false); }
    }, []);

    useEffect(() => { fetchDataForTab(activeTab); }, [activeTab, fetchDataForTab]);

   const fetchRootFolders = async (type) => {
        try {
            const response = await fetch(`${API_BASE_URL}/root-folders?type=${type}`);
            const data = await response.json();
            if (response.ok) {
                setArchiveFolders(data.folders);
                if (data.folders.length > 0) {
                    setSelectedArchiveFolder(data.folders[0].path);
                }
            } else {
                throw new Error(data.message || 'Failed to fetch root folders');
            }
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };
    const openArchiveDialog = (item) => {
        setCurrentArchiveItem(item);
        setIsArchiveDialogOpen(true);
        fetchRootFolders(item.type === 'tv' ? 'sonarr' : 'radarr');
    };

    const handleArchiveConfirm = async () => {
        if (!currentArchiveItem || !selectedArchiveFolder) return;
        
        try {
            const payloadItem = {
                id: currentArchiveItem.id,
                title: currentArchiveItem.title,
                type: currentArchiveItem.type,
                filePath: currentArchiveItem.filePath,
                sonarrId: currentArchiveItem.sonarrId,
                radarrId: currentArchiveItem.radarrId
            };
            
            const response = await fetch(`${API_BASE_URL}/content/${currentArchiveItem.id}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'archive',
                    item: payloadItem,
                    archivePath: selectedArchiveFolder
                }),
            });
            const resData = await response.json();
            if (!response.ok) { throw new Error(resData.message || `Failed to perform archive.`); }
            alert(resData.message);
            fetchDataForTab(activeTab);
            setIsArchiveDialogOpen(false);
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const executeAction = async (item, action) => {
        try {
            if (action === 'archive') {
                openArchiveDialog(item);
            } else if (action === 'delete') {
                // Extract only necessary fields to reduce payload size
                const payloadItem = {
                    id: item.id,
                    title: item.title,
                    type: item.type,
                    filePath: item.filePath,
                    sonarrId: item.sonarrId,
                    radarrId: item.radarrId
                };
                
                const response = await fetch(`${API_BASE_URL}/content/${item.id}/action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, item: payloadItem }),
                });
                const resData = await response.json();
                if (!response.ok) { throw new Error(resData.message || `Failed to perform ${action}.`); }
                alert(resData.message);
                fetchDataForTab(activeTab);
            }
        } catch (err) { alert(`Error: ${err.message}`); }
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
        } catch (err) { alert(`Error: ${err.message}`); }
    };

    const Dashboard = () => {
        if (loading) return <LoadingSpinner />;
        if (error) return <ErrorDisplay error={error} onRetry={() => fetchDataForTab('dashboard')} />;
        return (
            <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-xl font-semibold flex items-center mb-4"><HardDrive className="w-5 h-5 mr-2" />Storage Overview</h2>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <div className="text-center"><div className="text-2xl font-bold text-blue-600">{storageData.used?.toFixed(1)} GB</div><div className="text-gray-600">Used</div></div>
                        <div className="text-center"><div className="text-2xl font-bold text-green-600">{storageData.available?.toFixed(1)} GB</div><div className="text-gray-600">Available</div></div>
                        <div className="text-center"><div className="text-2xl font-bold text-orange-600">{potentialSavings.toFixed(1)} GB</div><div className="text-gray-600">Potential Savings</div></div>
                        <div className="text-center"><div className="text-2xl font-bold text-gray-800">{storageData.total?.toFixed(1)} GB</div><div className="text-gray-600">Total</div></div>
                    </div>
                </div>
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
                    <div className="bg-white rounded-lg shadow-md p-6"><div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold">Movies</h3><p className="text-2xl font-bold text-purple-600">{libraryStats.movies || 0}</p><p className="text-sm text-gray-600">{libraryStats.movies_size?.toFixed(1) || '0.0'} GB</p></div><Film className="w-8 h-8 text-purple-500" /></div></div>
                    <div className="bg-white rounded-lg shadow-md p-6"><div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold">On Streaming</h3><p className="text-2xl font-bold text-green-600">{libraryStats.onStreaming || 0}</p></div><ExternalLink className="w-8 h-8 text-green-500" /></div></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                            <Tv className="w-5 h-5 mr-2 text-blue-500" />
                            Largest Ended TV Shows
                        </h3>
                        <div className="space-y-3 max-h-96 overflow-y-auto">
                            {endedShows.length > 0 ? endedShows.map(item => (
                                <div key={`ended-${item.id}`} className="flex justify-between items-center p-3 border rounded">
                                    <div className="flex-1">
                                        <div className="font-medium">{item.title}</div>
                                        <div className="text-sm text-gray-600">
                                            {item.size} GB • {item.status}
                                        </div>
                                    </div>
                                </div>
                            )) : <div className="text-center text-gray-500 py-4">No ended shows found.</div>}
                        </div>
                    </div>
                    
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                            <Film className="w-5 h-5 mr-2 text-purple-500" />
                            Largest Movies on Streaming
                        </h3>
                        <div className="space-y-3 max-h-96 overflow-y-auto">
                            {streamingMovies.length > 0 ? streamingMovies.map(item => (
                                <div key={`streaming-${item.id}`} className="flex justify-between items-center p-3 border rounded">
                                    <div className="flex-1">
                                        <div className="font-medium">{item.title}</div>
                                        <div className="text-sm text-gray-600">
                                            {item.size} GB • Available on: {item.streamingServices.join(', ')}
                                        </div>
                                    </div>
                                </div>
                            )) : <div className="text-center text-gray-500 py-4">No streaming movies found.</div>}
                        </div>
                    </div>
                </div>
                
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h3 className="text-lg font-semibold mb-4">Recommended Actions</h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">{candidates.length > 0 ? candidates.map(item => (<div key={`${item.type}-${item.id}`} className="flex justify-between items-center p-3 border rounded"><div className="flex-1"><div className="font-medium">{item.title}</div><div className="text-sm text-gray-600">{item.size} GB • Last watched: {item.lastWatched || 'Never'}</div></div><div className="flex space-x-2 ml-4">{item.status === 'candidate-delete' && <button onClick={() => executeAction(item, 'delete')} className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 flex items-center"><Trash2 className="w-3 h-3 mr-1" />Delete</button>}{item.status === 'candidate-archive' && <button onClick={() => executeAction(item, 'archive')} className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 flex items-center"><Archive className="w-3 h-3 mr-1" />Archive</button>}</div></div>)) : <div className="text-center text-gray-500 py-4">No cleanup actions recommended.</div>}</div>
                </div>
            </div>
        );
    };

    const ContentManagement = () => {
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
        if (error) return <ErrorDisplay error={error} onRetry={() => fetchDataForTab('content')} />;

        return (
            <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-4 flex flex-col md:flex-row gap-4 items-center">
                    <div className="relative flex-grow w-full md:w-auto"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" /><input type="text" placeholder="Search by title..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full border rounded-lg px-10 py-2" /></div>
                    <div className="flex gap-4 w-full md:w-auto"><select value={contentFilter} onChange={(e) => setContentFilter(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 bg-white"><option value="all">All Content</option><option value="tv">TV Shows</option><option value="movies">Movies</option></select><select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 bg-white"><option value="size-desc">Sort by Size (High-Low)</option><option value="size-asc">Sort by Size (Low-High)</option><option value="title-asc">Sort by Title (A-Z)</option></select></div>
                </div>
                <div className="space-y-3">{paginatedItems.length > 0 ? paginatedItems.map(item => (<MediaItemCard key={`${item.type}-${item.id}`} item={item} onRuleChange={() => {}} onExecuteAction={executeAction} />)) : <div className="text-center text-gray-500 py-16 bg-white rounded-lg shadow-md"><p className="text-lg">No content found matching your criteria.</p></div>}</div>
                {totalPages > 1 && (<div className="flex justify-between items-center bg-white rounded-lg shadow-md p-4"><button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-4 py-2 bg-gray-200 text-gray-800 rounded disabled:opacity-50">Previous</button><span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span><button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-4 py-2 bg-gray-200 text-gray-800 rounded disabled:opacity-50">Next</button></div>)}
            </div>
        );
    };

    const SettingsPanel = () => {
        if (loading) return <LoadingSpinner />;
        if (error) return <ErrorDisplay error={error} onRetry={() => fetchDataForTab('settings')} />;
        return (
            <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-md p-6"><h3 className="text-lg font-semibold mb-4">Connection Status</h3><div className="grid grid-cols-1 md:grid-cols-3 gap-4">{Object.entries(connectionStatus).map(([service, status]) => (<div key={service} className={`p-3 border rounded ${status === 'Connected' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}><div className={`font-medium ${status === 'Connected' ? 'text-green-800' : 'text-red-800'}`}>{service.charAt(0).toUpperCase() + service.slice(1)}: {status}</div></div>))}</div></div>
                <div className="bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-xl font-semibold mb-4">Archive Folders</h2>
                    
                    <div className="mb-6">
                        <h3 className="text-lg font-semibold mb-2">TV Shows</h3>
                        <div className="space-y-2">
                            {settings.tvArchiveFolders?.map((folder, index) => (
                                <div key={`tv-${index}`} className="flex items-center">
                                    <div className="flex items-center justify-between w-full">
                                        <span className="text-gray-700 flex-1">{folder}</span>
                                        <button
                                            onClick={() => removeArchiveFolder('tv', index)}
                                            className="text-red-500 hover:text-red-700"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {(!settings.tvArchiveFolders || settings.tvArchiveFolders.length === 0) && (
                                <p className="text-gray-500">No TV archive folders configured</p>
                            )}
                        </div>
                        <button
                            onClick={() => fetchRootFolders('sonarr')}
                            className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                            Add from Sonarr
                        </button>
                    </div>
                    
                    <div className="mb-6">
                        <h3 className="text-lg font-semibold mb-2">Movies</h3>
                        <div className="space-y-2">
                            {settings.movieArchiveFolders?.map((folder, index) => (
                                <div key={`movie-${index}`} className="flex items-center">
                                    <div className="flex items-center justify-between w-full">
                                        <span className="text-gray-700 flex-1">{folder}</span>
                                        <button
                                            onClick={() => removeArchiveFolder('movie', index)}
                                            className="text-red-500 hover:text-red-700"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {(!settings.movieArchiveFolders || settings.movieArchiveFolders.length === 0) && (
                                <p className="text-gray-500">No movie archive folders configured</p>
                            )}
                        </div>
                        <button
                            onClick={() => fetchRootFolders('radarr')}
                            className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                            Add from Radarr
                        </button>
                    </div>
                    
                    <button onClick={handleSaveSettings} className="w-full bg-blue-500 text-white rounded py-3 hover:bg-blue-600 font-medium">Save All Settings</button>
                </div>
            </div>
        );
    };

    return (
        <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
            <div className="mb-6"><h1 className="text-3xl font-bold text-gray-800">Smart Storage Manager</h1><p className="text-gray-600">Automated Plex, Sonarr, and Radarr library optimization</p></div>
            <div className="mb-6"><div className="border-b border-gray-200"><nav className="-mb-px flex space-x-8">
                {[ { id: 'dashboard', name: 'Dashboard', icon: HardDrive }, { id: 'content', name: 'Content', icon: Play }, { id: 'logs', name: 'Logs', icon: FileText }, { id: 'settings', name: 'Settings', icon: Settings }].map(({ id, name, icon: Icon }) => (<button key={id} onClick={() => setActiveTab(id)} className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${activeTab === id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}><Icon className="w-4 h-4 mr-2" />{name}</button>))}
            </nav></div></div>
            {activeTab === 'dashboard' && <Dashboard />}
            {activeTab === 'content' && <ContentManagement />}
            {activeTab === 'logs' && <LogViewer />}
            {activeTab === 'settings' && <SettingsPanel />}

            {/* Archive Folder Selection Dialog */}
            {isArchiveDialogOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold mb-4">Select Archive Folder</h2>
                        <select
                            className="w-full border rounded px-3 py-2 mb-4"
                            value={selectedArchiveFolder}
                            onChange={(e) => setSelectedArchiveFolder(e.target.value)}
                        >
                            {archiveFolders.map(folder => (
                                <option key={folder.path} value={folder.path}>{folder.path}</option>
                            ))}
                        </select>
                        <div className="flex justify-end space-x-3">
                            <button
                                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                                onClick={() => setIsArchiveDialogOpen(false)}
                            >
                                Cancel
                            </button>
                            <button
                                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                                onClick={handleArchiveConfirm}
                            >
                                Archive
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SmartStorageManager;
import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { JOBS_DATA, REGIONS, JOB_TYPES } from '../data/jobsData';
import './Dashboard.css';

function Dashboard() {
  const { user, logout, trackEvent } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('All');
  const [selectedType, setSelectedType] = useState('All');
  const [activeTab, setActiveTab] = useState('All');

  // Track page view
  useEffect(() => {
    trackEvent('dashboard_view', { region: selectedRegion, type: selectedType });
  }, [selectedRegion, selectedType, trackEvent]);

  // Filter jobs based on search and filters
  const filteredJobs = useMemo(() => {
    let jobs = JOBS_DATA;

    // Filter by region
    if (selectedRegion !== 'All') {
      jobs = jobs.filter((job) => job.region === selectedRegion);
    }

    // Filter by job type
    if (selectedType !== 'All') {
      jobs = jobs.filter((job) => job.type === selectedType);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      jobs = jobs.filter(
        (job) =>
          job.daycare.toLowerCase().includes(query) ||
          job.role.toLowerCase().includes(query) ||
          job.region.toLowerCase().includes(query) ||
          job.schedule.toLowerCase().includes(query) ||
          job.status.toLowerCase().includes(query) ||
          job.description.toLowerCase().includes(query)
      );
    }

    return jobs;
  }, [searchQuery, selectedRegion, selectedType]);

  // Track search events
  useEffect(() => {
    if (searchQuery.trim()) {
      trackEvent('search', { query: searchQuery, resultCount: filteredJobs.length });
    }
  }, [searchQuery, filteredJobs.length, trackEvent]);

  // Track region filter changes
  const handleRegionChange = (region) => {
    setSelectedRegion(region);
    setActiveTab(region);
    trackEvent('filter_region', { region });
  };

  // Track type filter changes
  const handleTypeChange = (type) => {
    setSelectedType(type);
    trackEvent('filter_type', { type });
  };

  // Track tab clicks
  const handleTabClick = (region) => {
    setActiveTab(region);
    setSelectedRegion(region);
    trackEvent('region_tab_click', { region });
  };

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  // Generate Google search URL for daycare jobs in a specific region
  const getGoogleSearchUrl = (region = null, jobType = null) => {
    let query = 'daycare teacher jobs';
    
    if (region && region !== 'All') {
      query += ` ${region} BC`;
    } else {
      query += ' Vancouver area British Columbia';
    }
    
    if (jobType && jobType !== 'All') {
      query += ` ${jobType.toLowerCase()}`;
    }
    
    query += ' hiring ECE';
    
    const encodedQuery = encodeURIComponent(query);
    return `https://www.google.com/search?q=${encodedQuery}`;
  };

  const handleGoogleSearch = () => {
    const url = getGoogleSearchUrl(selectedRegion !== 'All' ? selectedRegion : null, selectedType !== 'All' ? selectedType : null);
    trackEvent('google_search_click', { region: selectedRegion, type: selectedType });
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <div className="pill">
            <span>CareLink</span> Daycare Jobs Hub
          </div>
          <h1>Vancouver Metro Daycare Roles</h1>
          <p>
            Browse {JOBS_DATA.length}+ open positions across Vancouver, Surrey,
            Langley, Abbotsford, Chilliwack, and surrounding areas.
          </p>
        </div>
        <div className="auth-bar">
          <span>
            {user?.name} ({user?.role})
          </span>
          <button className="btn btn-secondary" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>

      <main className="dashboard fade-in">
        <div className="toolbar">
          <input
            className="search"
            type="search"
            placeholder="Search daycare, role, region, schedule, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <select
            className="filter"
            value={selectedRegion}
            onChange={(e) => handleRegionChange(e.target.value)}
          >
            {REGIONS.map((region) => (
              <option key={region} value={region}>
                {region === 'All' ? 'All regions' : region}
              </option>
            ))}
          </select>
          <select
            className="filter"
            value={selectedType}
            onChange={(e) => handleTypeChange(e.target.value)}
          >
            {JOB_TYPES.map((type) => (
              <option key={type} value={type}>
                {type === 'All' ? 'All job types' : type}
              </option>
            ))}
          </select>
        </div>

        <div className="tabs">
          {REGIONS.filter((r) => r !== 'All').map((region) => (
            <button
              key={region}
              className={`tab ${activeTab === region ? 'active' : ''}`}
              onClick={() => handleTabClick(region)}
            >
              {region}
            </button>
          ))}
        </div>

        <section className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Daycare</th>
                <th>Region</th>
                <th>Role</th>
                <th>Schedule</th>
                <th>Pay</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="no-results">
                    <div>
                      <strong>No jobs found</strong>
                      <p>
                        Try adjusting your search or filters. Can't find what
                        you're looking for? Search on Google for more opportunities
                        {selectedRegion !== 'All' ? ` in ${selectedRegion}` : ' in other regions'}.
                      </p>
                      <button 
                        className="btn btn-google" 
                        onClick={handleGoogleSearch}
                        style={{ marginTop: '16px' }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                        </svg>
                        Search Google for {selectedRegion !== 'All' ? `${selectedRegion} ` : ''}Daycare Jobs
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <strong>{job.daycare}</strong>
                    </td>
                    <td>
                      <span className="badge">{job.region}</span>
                    </td>
                    <td>{job.role}</td>
                    <td>{job.schedule}</td>
                    <td>{job.pay}</td>
                    <td>
                      <span className={`status-badge status-${job.status.toLowerCase().replace(/\s+/g, '-')}`}>
                        {job.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <footer className="footer">
          <div>
            {filteredJobs.length === 0 ? (
              <div className="no-results-footer">
                <p>Can't find a match? Use the search box to refine or swap regions.</p>
                <button 
                  className="btn btn-google" 
                  onClick={handleGoogleSearch}
                  title="Search for more daycare jobs on Google"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Search on Google
                </button>
              </div>
            ) : (
              `Showing ${filteredJobs.length} of ${JOBS_DATA.length} positions`
            )}
          </div>
          <div className="footer-actions">
            <div className="results-count">
              {filteredJobs.length} {filteredJobs.length === 1 ? 'result' : 'results'}
            </div>
            <button 
              className="btn btn-google btn-small" 
              onClick={handleGoogleSearch}
              title={`Search Google for more daycare jobs${selectedRegion !== 'All' ? ` in ${selectedRegion}` : ' in Vancouver area'}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              More on Google
            </button>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default Dashboard;


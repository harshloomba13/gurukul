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
                        you're looking for? Use the search box to explore all
                        available positions.
                      </p>
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
            {filteredJobs.length === 0
              ? "Can't find a match? Use the search box to refine or swap regions."
              : `Showing ${filteredJobs.length} of ${JOBS_DATA.length} positions`}
          </div>
          <div className="results-count">
            {filteredJobs.length} {filteredJobs.length === 1 ? 'result' : 'results'}
          </div>
        </footer>
      </main>
    </div>
  );
}

export default Dashboard;


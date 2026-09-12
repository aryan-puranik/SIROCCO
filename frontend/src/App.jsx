import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import FleetOverview from './components/FleetOverview';
import ForecastVisualizer from './components/ForecastVisualizer';
import ExplainabilityStudio from './components/ExplainabilityStudio';
import WhatIfSimulator from './components/WhatIfSimulator';
import FaultAlertsTable from './components/FaultAlertsTable';
import GridDecisionEngine from './components/GridDecisionEngine';
import CalibrationBenchmark from './components/CalibrationBenchmark';

import {
  fetchPortfolioOverview,
  fetchSiteForecast,
  fetchExplainability,
  fetchAlerts,
  fetchRecommendations,
  fetchMetrics
} from './services/api';

export default function App() {
  const [overview, setOverview] = useState(null);
  const [sites, setSites] = useState([]);
  const [selectedSiteId, setSelectedSiteId] = useState('solar-fleet');
  const [horizon, setHorizon] = useState('48h');

  const [forecastData, setForecastData] = useState(null);
  const [explainabilityData, setExplainabilityData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [metricsData, setMetricsData] = useState(null);

  const [isLoadingForecast, setIsLoadingForecast] = useState(false);
  const [isLoadingExplain, setIsLoadingExplain] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard', 'simulator', 'benchmarks'

  // Initial Load
  const loadGlobalData = async () => {
    setIsRefreshing(true);
    try {
      const [ov, al, rec, met] = await Promise.all([
        fetchPortfolioOverview(),
        fetchAlerts(),
        fetchRecommendations(),
        fetchMetrics()
      ]);
      setOverview(ov);
      const loadedSites = ov.sites || [];
      setSites(loadedSites);
      if (loadedSites.length > 0 && !loadedSites.some(s => s.id === selectedSiteId)) {
        setSelectedSiteId(loadedSites[0].id);
      }
      setAlerts(al || []);
      setRecommendations(rec || []);
      setMetricsData(met || null);
    } catch (err) {
      console.error('Error loading global data:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadGlobalData();
  }, []);

  // Fetch site-specific forecast & explainability
  useEffect(() => {
    if (!selectedSiteId) return;

    let active = true;

    const loadSiteData = async () => {
      setIsLoadingForecast(true);
      setIsLoadingExplain(true);

      try {
        const [fc, exp] = await Promise.all([
          fetchSiteForecast(selectedSiteId, horizon),
          fetchExplainability(selectedSiteId)
        ]);
        if (active) {
          setForecastData(fc);
          setExplainabilityData(exp);
        }
      } catch (err) {
        console.error('Error loading site data:', err);
      } finally {
        if (active) {
          setIsLoadingForecast(false);
          setIsLoadingExplain(false);
        }
      }
    };

    loadSiteData();
    return () => { active = false; };
  }, [selectedSiteId, horizon]);

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <Navbar
        sites={sites}
        selectedSiteId={selectedSiteId}
        onSelectSite={setSelectedSiteId}
        onRefresh={loadGlobalData}
        isRefreshing={isRefreshing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800/80 gap-6">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'dashboard'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Operations & Forecast Studio
          </button>
          <button
            onClick={() => setActiveTab('simulator')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'simulator'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Digital Twin "What-If" Simulator
          </button>
          <button
            onClick={() => setActiveTab('benchmarks')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'benchmarks'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Model Performance & Calibration
          </button>
        </div>

        {/* Tab 1: Operations Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Fleet Overview KPIs */}
            <FleetOverview
              overview={overview}
              selectedSiteId={selectedSiteId}
              onSelectSite={setSelectedSiteId}
            />

            {/* Forecast & Explainability Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ForecastVisualizer
                  forecastData={forecastData}
                  horizon={horizon}
                  onSelectHorizon={setHorizon}
                  isLoading={isLoadingForecast}
                />
              </div>
              <div className="lg:col-span-1">
                <ExplainabilityStudio
                  data={explainabilityData}
                  isLoading={isLoadingExplain}
                />
              </div>
            </div>

            {/* Grid Decision Engine & Fault Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <GridDecisionEngine recommendations={recommendations} />
              <FaultAlertsTable alerts={alerts} />
            </div>
          </div>
        )}

        {/* Tab 2: What-If Simulator */}
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            <WhatIfSimulator />
          </div>
        )}

        {/* Tab 3: Model Calibration Benchmarks */}
        {activeTab === 'benchmarks' && (
          <div className="space-y-6">
            <CalibrationBenchmark metricsData={metricsData} />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-[#090d16] py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-2">
          <span>SIROCCO — AI Renewable Generation Forecasting Platform (Wind & Solar Fleet)</span>
          <span className="font-mono text-slate-400">LightGBM Quantile Models | pvlib Physics Engine</span>
        </div>
      </footer>

    </div>
  );
}

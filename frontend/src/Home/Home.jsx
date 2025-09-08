import React from "react";
import landingImage from '../images/landing-page.png';
import './Home.css';
import { useNavigate } from 'react-router-dom';
import { createPopup } from '@typeform/embed';
import '@typeform/embed/build/css/popup.css';

const Home = () => {
  const navigate = useNavigate();
  
  const openForm = () => {
    createPopup('bjiD63Uy', {
      mode: 'popup',   
      size: 100,     
      autoClose: 0     
    }).open();
  };

  const onLoginClick = (e) => {
    e?.preventDefault?.();
    console.log("Log In clicked → navigating to /auth");
    navigate("/auth");
  };

  return (
    <div className="landing-wrapper">
      <nav className="navbar">
        <div className="logo">PathNova</div>
        <div className="nav-links">
          <span className="nav-link inactive">Overview</span>
          <span className="nav-link active">Features</span>
          <span className="nav-link">FAQ</span>
          <button className="signin-btn" onClick={onLoginClick}>
            Sign In
          </button>

        </div>
      </nav>

      <main className="content">
        <div className="left">
          <h1 className="title">
            Your Personalized Career Coach – Tailored Guidance to Land Your
            Dream Job
          </h1>
          <p className="subtitle">
            Get custom study paths, project ideas, job tracking, and expert
            resources based on your goals
          </p>
          
          <button className="start-btn" onClick={openForm}>Start</button>
        </div>
        <div className="right">
          <img src={landingImage} alt="Career Coach" />
        </div>
      </main>
    </div>
  );
};
export default Home;

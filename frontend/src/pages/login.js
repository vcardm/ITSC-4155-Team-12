import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import '../bootstrap.darkly.css';


const Login = () => {

    const navigate = useNavigate()
    const [token, setToken] = useState(null)
    const [email, setEmail] = useState(null)
    const [password, setPassword] = useState(null)

    const handleSubmit = async(event) => {
        event.preventDefault();
        axios({
            method: "POST",
            url: "/login",
            data: {'email': email, "password": password}
        }).then(response => {
            const res = response.data;
            const temp_token = res.token;
            sessionStorage.setItem('token', temp_token);
            navigate("/", {replace:true});
        })
    }

    const handleEmail = (e) => {
        setEmail(e.target.value)
    }

    const handlePassword = (e) => {
        setPassword(e.target.value)
    }

    return(
        <div className="login-form-container">
            <form className="login-form" onSubmit={handleSubmit}>
                <div className="login-form-content">
                    <h3 className="login-form-title">Sign in</h3>
                    <div className="login-input-container">
                        <label className="login-input-title">Email Address:</label>
                        <input
                            type="email"
                            placeholder="Enter Email"
                            onChange={handleEmail}
                            className="form-control mt-1"
                        />
                    </div>
                    <div className="login-input-container">
                        <label className="login-input-title">Password:</label>
                        <input 
                            type="password"
                            placeholder="Enter Password"
                            onChange={handlePassword}
                            className="form-control mt-1"
                        />
                    </div>
                    <div className="login-submit-container">
                        <button type="submit" className="login-submit-button">Submit</button>
                    </div>
                </div>
            </form>
            <a href="/signup">Signup</a>
        </div>
    )
}

export default Login
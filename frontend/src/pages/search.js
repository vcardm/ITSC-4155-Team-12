import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import '../bootstrap.darkly.css';

const Search = () => {
    // new line start
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [movieData, setMovieData] = useState(null)
    const navigate = useNavigate();    
    
    const getData = async (event) => {
        event.preventDefault();
        setLoading(true)
        axios({
            method: "GET",
            url: "/list-search?query="+query
        }).then(response => {
            const res = response.data;
            setMovieData(({
                titles : res.titles,
                posters : res.poster_paths,
                length: res.length,
            }));
            setLoading(false)
        })
    }

    
    //end of new line

    return (
        <div>
        <div className="search-container">
            <h1 className="mb-5">Search the MovieDB Catalog</h1>
            <div className="search-form-container">
                <form onSubmit={getData}>
                        <label htmlFor="query-input-id" style={{"font-size":"24px"}}className="form-label">Enter Film Title:</label>
                        <input type="text"
                               className="search-form"
                               onChange={e => setQuery(e.target.value)}
                        />
                    <button type="submit" className="search-submit">Submit</button>
                </form>
            </div>
            {loading && !movieData &&
                <div>
                    <h1 className="loading"> Loading Films... </h1>
                </div>
            }
            {movieData && 
                <div className="film-grid">
                    <h1 className="film-grid-header">Welcome to MovieDB</h1>
                    <table className="film-grid-table">
                        <tbody>
                            <tr>
                                {movieData.titles.slice(0, 6).map((title, idx) => 
                                <td className="film-grid-td">
                                    <a className="film-grid-link-container" href={"/film/"+title}>
                                    <img className="film-grid-image" src={movieData.posters[idx]} ></img></a>
                                    <p className="film-grid-text">{title}</p>
                                    <button className="film-grid-button">Add to Queue</button>
                                    </td>
                                    )}
                            </tr>
                            <tr>
                                {movieData.titles.slice(6, 12).map((title, idx) => 
                                <td className="film-grid-td"><a className="film-grid-link-container" href={"/film/"+title}><img className="film-grid-image" src={movieData.posters[idx+6]} ></img></a><p className="film-grid-text">{title}</p></td>)}
                            </tr>
                            <tr>
                                {movieData.titles.slice(12, 18).map((title, idx) => 
                                <td className="film-grid-td"><a className="film-grid-link-container" href={"/film/"+title}><img className="film-grid-image" src={movieData.posters[idx+12]} ></img></a><p className="film-grid-text">{title}</p></td>)}
                            </tr>
                        </tbody>
                    </table>
                </div>
            }
            </div>
        </div>
    )
}

export default Search;

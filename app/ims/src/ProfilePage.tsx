import React, { useState } from "react";

interface ProfilePageProps {
  user: {
    name: string;
    role: string;
    email: string;
  };

  setUser: React.Dispatch<
    React.SetStateAction<{
      name: string;
      role: string;
      email: string;
    }>
  >;
}


const ProfilePage = ({ user, setUser }: ProfilePageProps) => {

  const [editing, setEditing] = useState(false);


  const [formData, setFormData] = useState({
    name: user.name,
    role: user.role,
    email: user.email,
  });



  const saveProfile = () => {

    setUser({
      name: formData.name,
      role: formData.role,
      email: formData.email,
    });

    setEditing(false);

  };



  return (

    <div className="profile-page">

      <style>{`

        .profile-page{
          min-height:100vh;
          background:#f7f5ff;
          padding:30px 60px;
          font-family:Inter, sans-serif;
          color:#1b075f;
        }



        .top-bar{

          display:flex;

          justify-content:flex-end;

          margin-bottom:20px;

        }



        .edit-btn{

          background:#5b21e8;

          color:white;

          border:none;

          padding:9px 18px;

          border-radius:12px;

          font-size:13px;

          font-weight:600;

          cursor:pointer;

          box-shadow:0 8px 20px rgba(91,33,232,.25);

        }




        .profile-header{

          background:linear-gradient(
            110deg,
            #35006b,
            #6d28d9
          );

          border-radius:26px;

          padding:32px;

          display:flex;

          align-items:center;

          gap:28px;

          color:white;

        }




        .avatar{

          width:90px;

          height:90px;

          border-radius:50%;

          background:#7c3aed;

          display:flex;

          align-items:center;

          justify-content:center;

          font-size:30px;

          font-weight:700;

          border:4px solid rgba(255,255,255,.35);

        }




        .name{

          font-size:26px;

          margin:0 0 8px;

          font-weight:700;

        }




        .role{

          display:inline-block;

          background:rgba(255,255,255,.15);

          border:1px solid rgba(255,255,255,.25);

          padding:5px 14px;

          border-radius:20px;

          font-size:13px;

        }




        .email{

          margin-top:12px;

          font-size:14px;

          opacity:.95;

        }




        .cards{

          display:grid;

          grid-template-columns:repeat(3,1fr);

          gap:22px;

          margin-top:30px;

        }




        .card{

          background:white;

          padding:22px;

          border-radius:20px;

          border:1px solid #ebe7ff;

        }




        .title{

          font-size:12px;

          color:#68709b;

          text-transform:uppercase;

          letter-spacing:1px;

        }




        .value{

          margin-top:10px;

          font-size:24px;

          font-weight:700;

          color:#1b075f;

        }




        .desc{

          margin-top:8px;

          color:#7882b5;

          font-size:13px;

        }




        .info{

          margin-top:35px;

          background:white;

          padding:30px;

          border-radius:24px;

        }




        .info h2{

          font-size:20px;

          margin-bottom:20px;

        }




        .row{

          display:flex;

          justify-content:space-between;

          align-items:center;

          padding:15px 0;

          border-bottom:1px solid #eee;

          font-size:14px;

        }




        .row span{

          color:#68709b;

        }




        .row strong{

          color:#1b075f;

          font-size:14px;

        }




        input{

          padding:8px 12px;

          border-radius:10px;

          border:1px solid #ddd;

          font-size:14px;

        }




        .save-btn{

          margin-top:20px;

          background:#5b21e8;

          color:white;

          border:none;

          padding:9px 20px;

          border-radius:12px;

          font-size:13px;

          cursor:pointer;

        }



        @media(max-width:900px){

          .cards{

            grid-template-columns:1fr;

          }

          .profile-page{

            padding:20px;

          }

        }


      `}</style>





      <div className="top-bar">

        <button
          className="edit-btn"
          onClick={() => setEditing(!editing)}
        >

          ✎ {editing ? "Cancel" : "Edit Profile"}

        </button>


      </div>





      <div className="profile-header">


        <div className="avatar">

          {user.name.charAt(0)}

        </div>




        <div>


          <h1 className="name">

            {user.name}

          </h1>



          <div className="role">

            {user.role}

          </div>




          <div className="email">

            {user.email}

          </div>


        </div>



      </div>






      <div className="cards">


        <div className="card">

          <div className="title">
            Assigned Locations
          </div>


          <div className="value">
            4
          </div>


          <div className="desc">
            Active inventory access
          </div>

        </div>




        <div className="card">

          <div className="title">
            Access Level
          </div>


          <div className="value">
            Manager
          </div>


          <div className="desc">
            Full inventory permissions
          </div>

        </div>





        <div className="card">

          <div className="title">
            Account Status
          </div>


          <div className="value">
            Active
          </div>


          <div className="desc">
            Verified account
          </div>


        </div>


      </div>







      <div className="info">


        <h2>
          Profile Information
        </h2>



        {

          editing ? (

            <>


              <div className="row">

                <span>
                  Name
                </span>


                <input

                  value={formData.name}

                  onChange={(e)=>

                    setFormData({

                      ...formData,

                      name:e.target.value

                    })

                  }

                />

              </div>




              <div className="row">

                <span>
                  Email
                </span>


                <input

                  value={formData.email}

                  onChange={(e)=>

                    setFormData({

                      ...formData,

                      email:e.target.value

                    })

                  }

                />


              </div>





              <div className="row">

                <span>
                  Role
                </span>


                <input

                  value={formData.role}

                  onChange={(e)=>

                    setFormData({

                      ...formData,

                      role:e.target.value

                    })

                  }

                />

              </div>




              <button
                className="save-btn"
                onClick={saveProfile}
              >

                Save Profile

              </button>



            </>



          ) : (


            <>


              <div className="row">

                <span>
                  Full Name
                </span>

                <strong>
                  {user.name}
                </strong>

              </div>




              <div className="row">

                <span>
                  Email
                </span>

                <strong>
                  {user.email}
                </strong>

              </div>





              <div className="row">

                <span>
                  Role
                </span>

                <strong>
                  {user.role}
                </strong>

              </div>



            </>


          )


        }


      </div>




    </div>

  );

};


export default ProfilePage;
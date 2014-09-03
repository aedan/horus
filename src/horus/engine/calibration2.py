#!/usr/bin/python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------#
#                                                                       #
# This file is part of the Horus Project                                #
#                                                                       #
# Copyright (C) 2014 Mundo Reader S.L.                                  #
#                                                                       #
# Date: June 2014                                                       #
# Author: Carlos Crespo <carlos.crespo@bq.com>                          #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                       #
#-----------------------------------------------------------------------#

__author__ = u"Carlos Crespo <carlos.crespo@bq.com>"
__license__ = u"GNU General Public License v3 http://www.gnu.org/licenses/gpl.html"

import cv2
import numpy as np
from scipy import optimize  
from horus.util import profile

class Calibration:
	"""Calibration class. For managing calibration"""
	def __init__(self, parent):

		self.parent=parent
		self.patternRows=profile.getProfileSettingInteger('pattern_rows') # points_per_column
		self.patternColumns=profile.getProfileSettingInteger('pattern_columns') # points_per_row
		self.squareWidth=profile.getProfileSettingInteger('square_width') # milimeters of each square's side

		self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.001)

		self.imagePointsStack=[]
		self.objPointsStack=[]

		self.objpoints=self.generateObjectPoints(self.patternColumns,self.patternRows,self.squareWidth)
		
		self.transVectors=[]

		self.centerEstimate=0,310
		self.linecolor=(240,246,0)
		self.lineThinckness=5
		self.firstPointData=[(288,326),(4,48),(20,20),			(412,198),(550,148),		(20,20),(20,20),		(210,350),(260,680),	(140,20),(20,20),(20,340),		(288,326),(288,326),(288,326),(288,326),(288,326),(288,326)]
		self.secondPointData=[(716,326),(596,168),(460,180),	(940,46),(940,20),			(940,20),(940,20),		(750,350),(700,680),	(940,20),(740,20),(500,500),		(716,326),(716,326),(716,326),(716,326),(716,326),(716,326)]
		self.thirdPointData=[(718,1026),(596,1140),(460,1000),	(940,1254),(940,1260),		(730,870),(720,550),	(940,1260),(940,1260),	(940,880),(450,600),(780,1260),	(718,1026),(718,1026),(718,1026),(718,1026),(718,1026),(718,1026)]
		self.forthPointData=[(286,1024),(4,1268),(20,1260),		(412,1140),(550,1076),		(192,870),(240,550),	(20,1260),(20,1260),	(480,740),(20,720),(20,1260),	(286,1024),(286,1024),(286,1024),(286,1024),(286,1024),(286,1024)]
		
		self.firstPoint=[]
		self.secondPoint=[]
		self.thirdPoint=[]
		self.forthPoint=[]
		

	def solvePnp(self,image):
		
		gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
		# the fast check flag reduces significantly the computation time if the pattern is out of sight 
		retval,corners=cv2.findChessboardCorners(gray,(self.patternColumns,self.patternRows),flags=cv2.CALIB_CB_FAST_CHECK)
		
		if retval:
			cv2.cornerSubPix(gray,corners,winSize=(11,11),zeroZone=(-1,-1),criteria=self.criteria)
			ret,rvecs,tvecs=cv2.solvePnP(self.objpoints,corners,self._calMatrix,self._distortionVector)
			self.transVectors.append(tvecs)
			# print (self.transVectors[2]+6.71+11*self.squareWidth)
		
		return retval

	def calibrationFromImages(self):
		if hasattr(self,'rvecs'):
			del self.rvecs[:]
			del self.tvecs[:]
		ret,self._calMatrix,self._distortionVector,self.rvecs,self.tvecs = cv2.calibrateCamera(self.objPointsStack,self.imagePointsStack,self.invertedShape)
		# print "Camera matrix: ",self._calMatrix
		
		self._distortionVector=self._distortionVector[0]
		# print np.array([self._distortionVector ])
		# print "Distortion coefficients: ", self._distortionVector
		# print "Rotation matrix: ",self.rvecs
		# print "Translation matrix: ",self.tvecs
		self.meanError()

	def detectPrintChessboard(self,image):

		
		gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
		self.invertedShape=gray.shape[::-1]
		retval,corners=cv2.findChessboardCorners(gray,(self.patternColumns,self.patternRows),flags=cv2.CALIB_CB_FAST_CHECK)
		if retval:
			cv2.cornerSubPix(gray,corners,winSize=(11,11),zeroZone=(-1,-1),criteria=self.criteria)
			self.imagePointsStack.append(corners)
			self.objPointsStack.append(self.objpoints)
			cv2.drawChessboardCorners(image,(self.patternColumns,self.patternRows),corners,retval)
			# imageToGuide = cv2.transpose(image)
			# imageToGuide = cv2.flip(image, 1)
			# imageToGuide=cv2.cvtColor(imageToGuide,cv2.COLOR_BGR2RGB)
			# cv2.imwrite('imageToGuide'+str(self.index)+'.jpg',imageToGuide)
		return image,retval

	def generateObjectPoints(self,patternColumns,patternRows,squareWidth):
		objp = np.zeros((patternRows*patternColumns,3), np.float32)
		objp[:,:2] = np.mgrid[0:patternColumns,0:patternRows].T.reshape(-1,2)
		objp=np.multiply(objp,12)
		return objp

	def clearData(self):
		del self.imagePointsStack[:]
		del self.objPointsStack[:]
		if hasattr(self,'rvecs'):
			del self.rvecs[:]
			del self.tvecs[:]

	def optimizeCircle(self,x2D,z2D):
		self.x2D=x2D
		self.z2D=z2D
		center,_=optimize.leastsq(self.f, self.centerEstimate)
		Ri     = self.calc_R(*center)
		return Ri,center

	def calc_R(self,xc, zc):
		return np.sqrt((self.x2D-xc)**2 + (self.z2D-zc)**2)

	def f(self,c):
		Ri = self.calc_R(*c)
		return Ri - Ri.mean()

	def setExtrinsic(self,xc,y,zc):
		
		self._transMatrix.itemset((0),xc)
		self._transMatrix.itemset((1),y)
		self._transMatrix.itemset((2),zc)
		self.saveTranslationVector()

	def meanError(self):
		mean_error = 0
		
		for i in xrange(len(self.objPointsStack)):
			imgpoints2,_=cv2.projectPoints(self.objPointsStack[i],self.rvecs[i],self.tvecs[i],self._calMatrix,self._distortionVector)
			error=cv2.norm(self.imagePointsStack[i],imgpoints2,cv2.NORM_L2)/len(imgpoints2)
			mean_error+=error
		self.mean_error=mean_error

	def undistortImage(self,image):

		mapx,mapy = cv2.initUndistortRectifyMap(self._calMatrix,self._distortionVector,R=None,newCameraMatrix=self._newCameraMatrix,size=(self.w,self.h),m1type=5)
		image = cv2.remap(image,mapx,mapy,cv2.INTER_LINEAR)
					
		return image

	def setGuides(self,frame,currentGrid):
		cv2.line(frame,self.firstPoint[currentGrid],self.secondPoint[currentGrid],self.linecolor,self.lineThinckness)
		cv2.line(frame,self.secondPoint[currentGrid],self.thirdPoint[currentGrid],self.linecolor,self.lineThinckness)
		cv2.line(frame,self.thirdPoint[currentGrid],self.forthPoint[currentGrid],self.linecolor,self.lineThinckness)
		cv2.line(frame,self.forthPoint[currentGrid],self.firstPoint[currentGrid],self.linecolor,self.lineThinckness)

		return frame

	def generateGuides(self,width,height):

		xfactor=width/960.
		yfactor=height/1280.

		self.firstPoint=[(int(a*xfactor),int(b*yfactor)) for (a,b) in self.firstPointData]
		self.secondPoint=[(int(a*xfactor),int(b*yfactor)) for (a,b) in self.secondPointData]
		self.thirdPoint=[(int(a*xfactor),int(b*yfactor)) for (a,b) in self.thirdPointData]
		self.forthPoint=[(int(a*xfactor),int(b*yfactor)) for (a,b) in self.forthPointData]



	# Data storage stuff

	def updateProfileToAllControls(self):

		self._calMatrix=profile.getProfileSettingNumpy('calibration_matrix')

		self._distortionVector=profile.getProfileSettingNumpy('distortion_vector')

		self._rotMatrix=profile.getProfileSettingNumpy('rotation_matrix')
		
		self._transMatrix=profile.getProfileSettingNumpy('translation_vector')	

		#undistort objects
		self.w,self.h=self.parent.scanner.camera.height,self.parent.scanner.camera.width
		self._newCameraMatrix, self.roi=cv2.getOptimalNewCameraMatrix(self._calMatrix,self._distortionVector,(self.w,self.h),alpha=1)
		

	def restoreCalibrationMatrix(self):
		profile.resetProfileSetting('calibration_matrix')
		self._calMatrix=profile.getProfileSettingNumpy('calibration_matrix')

	def restoreDistortionVector(self):
		profile.resetProfileSetting('distortion_vector')
		self._distortionVector=profile.getProfileSettingNumpy('distortion_vector')

	def restoreRotationMatrix(self):
		profile.resetProfileSetting('rotation_matrix')
		self._rotMatrix=profile.getProfileSettingNumpy('rotation_matrix')

	def restoreTranslationVector(self):
		profile.resetProfileSetting('translation_vector')
		self._transMatrix=profile.getProfileSettingNumpy('translation_vector')

	def saveCalibrationMatrix(self):
		profile.putProfileSettingNumpy('calibration_matrix',self._calMatrix)

	def saveDistortionVector(self):
		profile.putProfileSettingNumpy('distortion_vector',self._distortionVector)

	def saveRotationMatrix(self):
		profile.putProfileSettingNumpy('rotation_matrix',self._rotMatrix)
		

	def saveTranslationVector(self):
		profile.putProfileSettingNumpy('translation_vector',self._transMatrix)
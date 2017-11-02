/***********************************************************************
Copyright 2017 Google Inc.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Note that these code samples being shared are not official Google
products and are not formally supported.
************************************************************************/

angular.module('BlankApp', ['ngMaterial', 'ngCookies', 'ngclipboard'])
    .controller('AppController', [
      '$scope', '$http', '$cookies', '$mdToast',
      function AppController($scope, $http, $cookies, $mdToast) {
        $scope.trackers = {};
        $scope.profileChanged = function() {
          $cookies.put('lastProfileId', $scope.profile);
        };
        $scope.profileLoading = true;
        $http.get('/profiles').then(function(r) {
          $scope.profileLoading = false;
          $scope.profiles = r.data.profiles;
          const profileId = $cookies.get('lastProfileId');
          if (profileId && $scope.profiles.some(function(p) {
                return p.profileId == profileId;
              })) {
            $scope.profile = profileId;
          }
        }, errorHandler(function() {
                                      $scope.profileLoading = false;
                                    }));

        $scope.search = function(text) {
          $scope.placementLoading = true;
          return $http
              .get('/profiles/' + $scope.profile + '/placements/' + text)
              .then(function(d) {
                $scope.placementLoading = false;
                $scope.placementNotFound = false;
                $scope.placement = d.data.placement;
                $scope.placement.url = getPlacementUrl(
                    $scope.placement.accountId, $scope.placement.campaignId,
                    $scope.placement.id);
                return d;
              }, errorHandler(function(err) {
                      $scope.placementLoading = false;
                      if (err.code != 404) {
                        $mdToast.showSimple(err);
                      }
                      $scope.placementNotFound = true;
                      $scope.placement = null;
                    }));
        };

        $scope.parse = function() {
          // check separator - either Excel style \t or comma
          let separator = '\t';
          if ($scope.trackers.csv.indexOf(separator) === -1) {
            separator = ',';
          }
          $scope.trackers.parsed = [];
          $scope.trackers.csv.split('\n').forEach(function(l) {
            const data = l.split(separator).map(function(x) {
              return x.trim();
            });
            if (data.length !== 2) {
              $mdToast.showSimple('Invalid CSV: ' + l);
              $scope.trackers = [];
              return;
            }
            $scope.trackers.parsed.push({'name': data[0], 'url': data[1]});
          });
        };

        $scope.upload = function() {
          $scope.trackers.uploading = true;
          $http
              .post(
                  '/profiles/' + $scope.profile + '/placements/' +
                      $scope.placement.id,
                  {trackers: $scope.trackers.parsed})
              .then(function(d) {
                $scope.trackers.uploading = false;
                for (var tkey in $scope.trackers.parsed) {
                  const t = $scope.trackers.parsed[tkey];
                  for (var ukey in d.data.uploaded) {
                    const up = d.data.uploaded[ukey];
                    if (t.name == up.name) {
                      t.id = ukey;
                      t.clickUrl = up.clickUrl;
                    }
                  }
                }
                $scope.trackers.uploaded = true;
                $scope.trackers.uploadedCsv =
                    $scope.trackers.parsed
                        .map(function(t) {
                          return [t.name, t.url, t.id, t.clickUrl].join(',');
                        })
                        .join('\n');
              }, errorHandler(function() {
                      $scope.trackers.uploading = false;
                    }));
        };

        $scope.onSuccess = function(e) {
          $mdToast.showSimple('Copied to clipboard');
        };
      }
    ]);

function getPlacementUrl(accountId, campaignId, placementId) {
  return 'https://ddm.google.com/dfa/trafficking/#/accounts/' + accountId +
      '/campaigns/' + campaignId + '/explorer?statuses=0;2#%2Fplacements%2F' +
      placementId;
}

function errorHandler(callback) {
  return function(reason) {
    return callback(reason.data);
  };
}
